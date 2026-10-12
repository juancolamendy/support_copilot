"""Deterministic rules: no LLM and no I/O; inputs are passed in."""

from __future__ import annotations

from collections import Counter
from collections.abc import Collection, Iterable, Sequence

from .tools import _terms
from .types import KnowledgeDocument, ServiceOwner

CONFIDENCE_THRESHOLD = 0.70
PREFIX_LENGTH = 5


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


def _term_found(term: str, document_terms: set[str]) -> bool:
    """Exact match, or a shared first-five-letters prefix (a crude stem)."""
    if term in document_terms:
        return True
    if len(term) < PREFIX_LENGTH:
        return False
    prefix = term[:PREFIX_LENGTH]
    return any(
        len(other) >= PREFIX_LENGTH and other.startswith(prefix)
        for other in document_terms
    )


def confidence(query_terms: Collection[str], document: KnowledgeDocument) -> float:
    """Share of query terms found in the document title or body, from 0 to 1.

    "expiration" matches "expire" and "resend" matches "resending", because the
    real model's terms do not match the document's word forms exactly (DES-027).
    """
    if not query_terms:
        return 0.0
    document_terms = _terms(f"{document.title} {document.content}")
    found = sum(1 for term in query_terms if _term_found(term, document_terms))
    return found / len(query_terms)
