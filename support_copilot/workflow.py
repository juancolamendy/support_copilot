"""Support workflow graph (DES-002, DES-009, DES-010).

Guardrails live in graph edges, not prompts: early stops on missing data or a
known incident, a confidence gate before drafting, and deterministic escalation.
Only `extract` and `draft` call the LLM.
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from .fixture_store import load_owners
from .llm import (
    MAX_PROMPT_DOCUMENTS,
    LLMFailure,
    draft_answer,
    extract_details,
    get_model,
)
from .rules import CONFIDENCE_THRESHOLD, confidence, detect_area, filter_docs
from .tools import _terms
from .types import (
    Citation,
    CopilotTools,
    ServiceOwner,
    SupportResult,
    SupportTicket,
    TicketDetails,
    WorkflowState,
)

logger = logging.getLogger(__name__)

Node = Callable[[WorkflowState], Awaitable[dict[str, Any]]]


def _error(message: str) -> SupportResult:
    return SupportResult(status="error", error_message=message)


def escalate_human(area: str, owner: ServiceOwner | None) -> None:
    """Tell the human where to route the ticket (AS06).

    Written to stderr so stdout stays a single JSON result for the CLI.
    """
    if owner is None:
        print(f"ESCALATE area={area}: no owner found", file=sys.stderr)
        return
    print(
        f"ESCALATE team={owner.team} area={area} channel={owner.escalation_channel}",
        file=sys.stderr,
    )


def _query_terms(ticket: SupportTicket, details: TicketDetails) -> set[str]:
    return _terms(ticket.title) | _terms(" ".join(details.product_terms))


def _logged(name: str, node: Node) -> Node:
    """One log line per node, and a safe error result if the node raises.

    Neither the log nor the error message contains ticket text or exception text
    (DES-021, DES-023).
    """

    async def run(state: WorkflowState) -> dict[str, Any]:
        started = time.perf_counter()
        failure = ""
        try:
            update = await node(state)
            outcome = "stop" if "result" in update else "continue"
        except Exception as error:  # noqa: BLE001 - workflow boundary, see _error
            failure = type(error).__name__
            update = {"result": _error(f"{name} step failed: {failure}")}
            outcome = "error"
        elapsed_ms = (time.perf_counter() - started) * 1000
        detail = f" error={failure}" if failure else ""
        logger.info(
            "node=%s outcome=%s%s duration_ms=%d", name, outcome, detail, elapsed_ms
        )
        return update

    return run


def _stop_or(next_node: str) -> Callable[[WorkflowState], str]:
    """Route to END as soon as a node has produced the final result."""

    def route(state: WorkflowState) -> str:
        return END if "result" in state else next_node

    return route


def _route_after_search(state: WorkflowState) -> str:
    """Escalate when nothing approved was found or confidence is below the cutoff."""
    if "result" in state:
        return END
    score = state.get("confidence_score")
    if score is None or score < CONFIDENCE_THRESHOLD:
        return "escalate"
    return "draft"


class _Steps:
    """Graph nodes; each returns a partial state update."""

    def __init__(
        self,
        tools: CopilotTools,
        model: BaseChatModel | None,
        owners: Sequence[ServiceOwner],
    ) -> None:
        self.tools = tools
        self.model = model
        self.owners = owners

    async def validate(self, state: WorkflowState) -> dict[str, Any]:
        if state["ticket"].description.strip():
            return {}
        return {"result": _error("missing required field: description")}

    async def extract(self, state: WorkflowState) -> dict[str, Any]:
        chat_model = self.model if self.model is not None else get_model()
        details = await extract_details(chat_model, state["ticket"])
        if isinstance(details, LLMFailure):
            return {"result": _error(details.message)}
        return {"details": details}

    async def find_area(self, state: WorkflowState) -> dict[str, Any]:
        ticket = state["ticket"]
        area = detect_area(ticket.title, ticket.description, self.owners)
        if area is None:
            return {"result": _error("missing required field: area (none detected)")}
        return {"area": area}

    async def check_incident(self, state: WorkflowState) -> dict[str, Any]:
        area = state["area"]
        incidents = await self.tools.find_active_incidents(area)
        if not incidents:
            return {"incident": None}
        latest = max(incidents, key=lambda item: item.updated_at)
        owner = await self.tools.find_owner(area)
        notes = [] if owner else ["no owner found for area"]
        result = SupportResult(
            status="ok", incident=latest, owner=owner, area=area, notes=notes
        )
        return {"incident": latest, "result": result}

    async def search(self, state: WorkflowState) -> dict[str, Any]:
        ticket, details = state["ticket"], state["details"]
        query = f"{ticket.title} {' '.join(details.product_terms)}"
        documents = filter_docs(await self.tools.search_knowledge(query))
        score = None
        if documents:
            score = confidence(_query_terms(ticket, details), documents[0])
        return {"documents": documents, "confidence_score": score}

    async def escalate(self, state: WorkflowState) -> dict[str, Any]:
        area = state["area"]
        owner = await self.tools.find_owner(area)
        escalate_human(area, owner)
        reason = (
            "no approved knowledge found"
            if not state["documents"]
            else "confidence below threshold"
        )
        notes = [reason] + ([] if owner else ["no owner found for area"])
        result = SupportResult(
            status="ok",
            escalate=True,
            owner=owner,
            area=area,
            confidence_score=state.get("confidence_score"),
            notes=notes,
        )
        return {"result": result}

    async def draft(self, state: WorkflowState) -> dict[str, Any]:
        ticket, details = state["ticket"], state["details"]
        terms = _query_terms(ticket, details)
        scored = [(doc, confidence(terms, doc)) for doc in state["documents"]]
        evidence = [
            (doc, score) for doc, score in scored if score >= CONFIDENCE_THRESHOLD
        ][:MAX_PROMPT_DOCUMENTS]
        chat_model = self.model if self.model is not None else get_model()
        answer = await draft_answer(chat_model, details, [doc for doc, _ in evidence])
        if isinstance(answer, LLMFailure):
            return {"result": _error(answer.message)}
        # Citations come from the documents sent to the model, never from its text.
        citations = [
            Citation(source_id=doc.id, reason=f"confidence {score:.2f}")
            for doc, score in evidence
        ]
        result = SupportResult(
            status="ok",
            response=answer.response,
            citations=citations,
            confidence_score=state["confidence_score"],
            area=state["area"],
        )
        return {"response": answer.response, "result": result}


def build_workflow(
    tools: CopilotTools,
    model: BaseChatModel | None = None,
    owners: Sequence[ServiceOwner] | None = None,
):
    """Compile the workflow; `model` and `owners` default to production sources."""
    steps = _Steps(tools, model, owners if owners is not None else load_owners())
    chain: list[tuple[str, Node]] = [
        ("validate", steps.validate),
        ("extract", steps.extract),
        ("detect_area", steps.find_area),
        ("check_incident", steps.check_incident),
        ("search", steps.search),
    ]
    graph = StateGraph(WorkflowState)
    for name, node in chain + [("escalate", steps.escalate), ("draft", steps.draft)]:
        graph.add_node(name, _logged(name, node))
    graph.add_edge(START, "validate")
    for (name, _), (next_name, _) in zip(chain, chain[1:]):
        graph.add_conditional_edges(name, _stop_or(next_name), [next_name, END])
    targets = ["escalate", "draft", END]
    graph.add_conditional_edges("search", _route_after_search, targets)
    graph.add_edge("escalate", END)
    graph.add_edge("draft", END)
    return graph.compile()
