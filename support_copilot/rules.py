"""Deterministic rules: no LLM and no I/O; inputs are passed in."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

from .tools import _terms
from .types import KnowledgeDocument, ServiceOwner


def _unique_area_terms(owners: Sequence[ServiceOwner]) -> dict[str, set[str]]:
    """Terms from each area name, minus terms shared with another area."""
    terms_by_area = {
        owner.area: _terms(owner.area.replace("-", " ")) for owner in owners
    }
    counts = Counter(term for terms in terms_by_area.values() for term in terms)
    return {
        area: {term for term in terms if counts[term] == 1}
        for area, terms in terms_by_area.items()
    }


def detect_area(
    title: str, description: str, owners: Sequence[ServiceOwner]
) -> str | None:
    """Pick the owner area whose name terms best match the ticket text.

    The most matched terms win, then the longest matched term, then the order
    of `owners`. Returns None when no area term appears.
    """
    ticket_terms = _terms(f"{title} {description}")
    best_area: str | None = None
    best_key = (0, 0)
    for area, terms in _unique_area_terms(owners).items():
        matched = terms & ticket_terms
        if not matched:
            continue
        key = (len(matched), max(len(term) for term in matched))
        if key > best_key:
            best_area, best_key = area, key
    return best_area


def filter_docs(documents: Iterable[KnowledgeDocument]) -> list[KnowledgeDocument]:
    """Keep only documents that are approved and internal."""
    return [
        document
        for document in documents
        if document.status == "approved" and document.access == "internal"
    ]
