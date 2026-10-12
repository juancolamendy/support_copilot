from __future__ import annotations

import re
from dataclasses import replace

from .fixture_store import load_incidents, load_knowledge, load_owners
from .mock_model import MockLanguageModel
from .types import Incident, KnowledgeDocument, ServiceOwner

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
