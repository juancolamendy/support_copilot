"""Support workflow graph: validation, extraction, area and incident stop.

Guardrails live in graph edges, not prompts (DES-002, DES-009, DES-010). Later
phases extend the graph after `check_incident`.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from .fixture_store import load_owners
from .llm import LLMFailure, extract_details, get_model
from .rules import detect_area
from .types import CopilotTools, ServiceOwner, SupportResult, WorkflowState

logger = logging.getLogger(__name__)

Node = Callable[[WorkflowState], Awaitable[dict[str, Any]]]


def _error(message: str) -> SupportResult:
    return SupportResult(status="error", error_message=message)


def _logged(name: str, node: Node) -> Node:
    """One structured log line per node; never includes ticket text (DES-023)."""

    async def run(state: WorkflowState) -> dict[str, Any]:
        started = time.perf_counter()
        outcome = "error"
        try:
            update = await node(state)
            outcome = "stop" if "result" in update else "continue"
            return update
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info("node=%s outcome=%s duration_ms=%d", name, outcome, elapsed_ms)

    return run


def _stop_or(next_node: str) -> Callable[[WorkflowState], str]:
    """Route to END as soon as a node has produced the final result."""

    def route(state: WorkflowState) -> str:
        return END if "result" in state else next_node

    return route


def build_workflow(
    tools: CopilotTools,
    model: BaseChatModel | None = None,
    owners: Sequence[ServiceOwner] | None = None,
):
    """Compile the workflow; `model` and `owners` default to production sources."""
    area_owners = owners if owners is not None else load_owners()

    async def validate(state: WorkflowState) -> dict[str, Any]:
        if state["ticket"].description.strip():
            return {}
        return {"result": _error("missing required field: description")}

    async def extract(state: WorkflowState) -> dict[str, Any]:
        chat_model = model if model is not None else get_model()
        details = await extract_details(chat_model, state["ticket"])
        if isinstance(details, LLMFailure):
            return {"result": _error(details.message)}
        return {"details": details}

    async def find_area(state: WorkflowState) -> dict[str, Any]:
        ticket = state["ticket"]
        area = detect_area(ticket.title, ticket.description, area_owners)
        if area is None:
            return {"result": _error("missing required field: area (none detected)")}
        return {"area": area}

    async def check_incident(state: WorkflowState) -> dict[str, Any]:
        area = state["area"]
        incidents = await tools.find_active_incidents(area)
        if not incidents:
            return {"incident": None}
        latest = max(incidents, key=lambda item: item.updated_at)
        owner = await tools.find_owner(area)
        notes = [] if owner else ["no owner found for area"]
        result = SupportResult(
            status="ok", incident=latest, owner=owner, area=area, notes=notes
        )
        return {"incident": latest, "result": result}

    async def pending(state: WorkflowState) -> dict[str, Any]:
        return {"result": _error("knowledge search is not implemented yet")}

    steps: list[tuple[str, Node]] = [
        ("validate", validate),
        ("extract", extract),
        ("detect_area", find_area),
        ("check_incident", check_incident),
        ("pending", pending),
    ]
    graph = StateGraph(WorkflowState)
    for name, node in steps:
        graph.add_node(name, _logged(name, node))
    graph.add_edge(START, "validate")
    for (name, _), (next_name, _) in zip(steps, steps[1:]):
        graph.add_conditional_edges(name, _stop_or(next_name), [next_name, END])
    graph.add_edge("pending", END)
    return graph.compile()
