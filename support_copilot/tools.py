from __future__ import annotations

import re
from dataclasses import asdict, replace
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from .fixture_store import load_incidents, load_knowledge, load_owners, load_tickets
from .mock_model import MockLanguageModel
from .types import CopilotTools, Incident, KnowledgeDocument, ServiceOwner

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "the",
    "to",
    "with",
}


def _terms(value: str) -> set[str]:
    return {
        term
        for term in re.sub(r"[^a-z0-9]+", " ", value.lower()).split()
        if len(term) > 1 and term not in STOP_WORDS
    }


def _score(query_terms: set[str], document: KnowledgeDocument) -> int:
    title_terms = _terms(document.title)
    document_terms = _terms(f"{document.title} {document.content}")
    return sum(
        3 if term in title_terms else 1 if term in document_terms else 0
        for term in query_terms
    )


class FixtureTools:
    def __init__(self) -> None:
        self.model = MockLanguageModel()

    async def search_knowledge(
        self, query: str, limit: int = 5
    ) -> list[KnowledgeDocument]:
        query_terms = _terms(query)
        scored = [
            replace(document, score=_score(query_terms, document))
            for document in load_knowledge()
        ]
        return sorted(
            (document for document in scored if document.score > 0),
            key=lambda document: document.score,
            reverse=True,
        )[:limit]

    async def find_owner(self, area: str) -> ServiceOwner | None:
        return next(
            (owner for owner in load_owners() if owner.area.lower() == area.lower()),
            None,
        )

    async def find_active_incidents(self, area: str | None = None) -> list[Incident]:
        return [
            incident
            for incident in load_incidents()
            if incident.status != "resolved"
            and (area is None or incident.area.lower() == area.lower())
        ]


def create_fixture_tools() -> FixtureTools:
    return FixtureTools()


def build_langchain_tools(tools: CopilotTools) -> list[BaseTool]:
    """Expose the four fixtures as LangChain tools that delegate to `tools`."""

    async def get_ticket(ticket_id: str) -> dict[str, Any]:
        """Look up a support ticket by its id."""
        ticket = next((t for t in load_tickets() if t.id == ticket_id), None)
        if ticket is None:
            return {"error": f"ticket not found: {ticket_id}"}
        return asdict(ticket)

    async def find_active_incidents(area: str | None = None) -> list[dict[str, Any]]:
        """List unresolved incidents, optionally limited to one area."""
        return [asdict(item) for item in await tools.find_active_incidents(area)]

    async def search_knowledge(query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search the knowledge base; each result carries a relevance score."""
        return [asdict(doc) for doc in await tools.search_knowledge(query, limit)]

    async def find_owner(area: str) -> dict[str, Any]:
        """Find the team and escalation channel that own a product area."""
        owner = await tools.find_owner(area)
        if owner is None:
            return {"error": f"no owner found for area: {area}"}
        return asdict(owner)

    functions = (get_ticket, find_active_incidents, search_knowledge, find_owner)
    return [StructuredTool.from_function(coroutine=function) for function in functions]
