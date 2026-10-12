"""Confidence score checks for TASK-004 (REQ-F-006a, DES-008, DES-027)."""

from __future__ import annotations

import pytest

from support_copilot.fixture_store import load_knowledge, load_tickets
from support_copilot.rules import CONFIDENCE_THRESHOLD, confidence, filter_docs
from support_copilot.tools import _terms, create_fixture_tools

# Canned extraction output: the product_terms a model would plausibly return.
CANNED_PRODUCT_TERMS = {
    "TCK-1001": ["password", "reset", "email", "link"],
    "TCK-1002": ["invitation", "expired", "portal", "link"],
}
EXPECTED_TOP_DOCUMENT = {"TCK-1001": "KB-101", "TCK-1002": "KB-103"}


def _document(document_id: str):
    return next(doc for doc in load_knowledge() if doc.id == document_id)


def _ticket(ticket_id: str):
    return next(ticket for ticket in load_tickets() if ticket.id == ticket_id)


def test_005_confidence_is_one_when_every_term_is_in_the_document() -> None:
    """[TEST-005][AC-007][REQ-F-006a][DES-027][TASK-004] full coverage scores 1.0."""
    assert confidence({"password", "reset"}, _document("KB-101")) == 1.0


def test_005_confidence_is_the_share_of_terms_found_in_the_document() -> None:
    """[TEST-005][AC-007][REQ-F-006a][DES-027][TASK-004] half the terms give 0.5."""
    terms = {"password", "reset", "zzzzz", "qqqqq"}

    assert confidence(terms, _document("KB-101")) == 0.5


def test_005_confidence_counts_terms_found_only_in_the_body() -> None:
    """[TEST-005][AC-007][DES-027][TASK-004] title and body both count."""
    document = _document("KB-101")

    assert "email" not in _terms(document.title)
    assert confidence({"email"}, document) == 1.0


def test_005_confidence_is_zero_when_no_term_overlaps() -> None:
    """[TEST-005][AC-007][DES-027][TASK-004] no overlap means no confidence."""
    assert confidence({"printer", "jams"}, _document("KB-101")) == 0.0


def test_005_confidence_is_zero_for_an_empty_term_set() -> None:
    """[TEST-005][AC-007][DES-027][TASK-004] an empty query never divides by zero."""
    assert confidence(set(), _document("KB-101")) == 0.0


def test_005_confidence_is_deterministic_and_within_bounds() -> None:
    """[TEST-005][AC-007][DES-027][TASK-004] same input, same score, always 0 to 1."""
    term_sets = [{"password"}, {"portal", "invitation", "zzzzz"}, {"scheduling"}]

    for document in load_knowledge():
        for terms in term_sets:
            first = confidence(terms, document)
            assert first == confidence(terms, document)
            assert 0.0 <= first <= 1.0


def test_005_confidence_threshold_is_seventy_percent() -> None:
    """[TEST-005][AC-007][REQ-F-006a][DES-027][TASK-004] the cutoff is 0.70."""
    assert CONFIDENCE_THRESHOLD == 0.70


@pytest.mark.parametrize("ticket_id", ["TCK-1001", "TCK-1002"])
async def test_006_answerable_fixture_tickets_reach_the_threshold(
    ticket_id: str,
) -> None:
    """[TEST-006][AC-001][REQ-F-006a][DES-027][TASK-004] cutoff is reachable (R1)."""
    ticket = _ticket(ticket_id)
    product_terms = CANNED_PRODUCT_TERMS[ticket_id]
    query = f"{ticket.title} {' '.join(product_terms)}"
    query_terms = _terms(ticket.title) | _terms(" ".join(product_terms))

    hits = filter_docs(await create_fixture_tools().search_knowledge(query))
    top = hits[0]

    assert top.id == EXPECTED_TOP_DOCUMENT[ticket_id]
    assert confidence(query_terms, top) >= CONFIDENCE_THRESHOLD


async def test_006_unrelated_query_has_no_confidence_in_any_approved_document() -> None:
    """[TEST-006][AC-001][DES-027][TASK-004] low coverage must not pass the cutoff."""
    query_terms = _terms("printer jams office")

    approved = filter_docs(load_knowledge())

    assert approved
    assert all(confidence(query_terms, doc) < CONFIDENCE_THRESHOLD for doc in approved)
