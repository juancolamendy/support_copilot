"""Deterministic rule checks for TASK-003 (REQ-F-003a, REQ-F-005, DES-004/008/020)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from support_copilot.fixture_store import load_knowledge, load_owners, load_tickets
from support_copilot.rules import detect_area, filter_docs
from support_copilot.types import ServiceOwner


def _owner(area: str) -> ServiceOwner:
    return ServiceOwner(area=area, team=f"{area} team", escalation_channel=f"#{area}")


def _fixture_ticket(ticket_id: str):
    return next(ticket for ticket in load_tickets() if ticket.id == ticket_id)


@pytest.mark.parametrize(
    ("ticket_id", "expected_area"),
    [
        ("TCK-1001", "patient-portal"),
        ("TCK-1002", "patient-portal"),
        ("TCK-1003", "scheduling"),
    ],
)
def test_003_detect_area_maps_fixture_tickets_to_their_owner_area(
    ticket_id: str, expected_area: str
) -> None:
    """[TEST-003][AC-005][REQ-F-003a][DES-004][TASK-003] fixture tickets resolve."""
    ticket = _fixture_ticket(ticket_id)

    area = detect_area(ticket.title, ticket.description, load_owners())

    assert area == expected_area


def test_003_detect_area_returns_none_when_no_area_term_appears() -> None:
    """[TEST-003][AC-005][REQ-F-003a][DES-004][TASK-003] no match means no area."""
    area = detect_area("Printer jams", "The printer keeps jamming", load_owners())

    assert area is None


def test_003_detect_area_returns_none_for_empty_text_or_no_owners() -> None:
    """[TEST-003][AC-005][REQ-F-003a][DES-004][TASK-003] empty inputs: no area."""
    assert detect_area("", "", load_owners()) is None
    assert detect_area("Portal invitation", "expired", []) is None


def test_003_detect_area_ignores_case_and_punctuation() -> None:
    """[TEST-003][AC-005][DES-008][TASK-003] tokenizing matches the search tokenizer."""
    area = detect_area("SCHEDULING!!", "slots are (blank)", load_owners())

    assert area == "scheduling"


def test_003_detect_area_ignores_terms_shared_by_more_than_one_area() -> None:
    """[TEST-003][AC-005][DES-026][TASK-003] a shared term cannot decide the area."""
    owners = [_owner("patient-portal"), _owner("patient-billing")]

    assert detect_area("Patient cannot sign in", "please help", owners) is None
    assert detect_area("Patient portal down", "cannot sign in", owners) == (
        "patient-portal"
    )


def test_003_detect_area_prefers_the_area_with_more_matched_terms() -> None:
    """[TEST-003][AC-005][DES-026][TASK-003] more matched terms win."""
    owners = [_owner("alpha-beta"), _owner("gamma-delta")]

    area = detect_area("gamma delta alpha", "details", owners)

    assert area == "gamma-delta"


def test_003_detect_area_breaks_equal_counts_by_longest_matched_term() -> None:
    """[TEST-003][AC-005][DES-026][TASK-003] longest match, then ownership order."""
    owners = [_owner("alpha-beta"), _owner("gamma-epsilon")]

    assert detect_area("alpha epsilon", "details", owners) == "gamma-epsilon"
    assert detect_area("alpha gamma", "details", owners) == "alpha-beta"


def test_004_filter_docs_keeps_only_approved_internal_documents() -> None:
    """[TEST-004][AC-008][REQ-F-005][DES-020][TASK-003] fixture KB is filtered."""
    kept = filter_docs(load_knowledge())

    assert [document.id for document in kept] == ["KB-101", "KB-103", "KB-104"]


def test_004_filter_docs_drops_deprecated_draft_and_restricted_documents() -> None:
    """[TEST-004][AC-008][DES-028][TASK-003] KB-102, KB-105 and KB-106 never pass."""
    kept_ids = {document.id for document in filter_docs(load_knowledge())}

    assert kept_ids.isdisjoint({"KB-102", "KB-105", "KB-106"})


def test_004_filter_docs_checks_status_and_access_independently() -> None:
    """[TEST-004][AC-008][DES-028][TASK-003] each condition excludes on its own."""
    approved_internal = next(d for d in load_knowledge() if d.id == "KB-101")
    draft_internal = replace(approved_internal, id="X-DRAFT", status="draft")
    approved_restricted = replace(
        approved_internal, id="X-RESTRICTED", access="restricted"
    )

    kept = filter_docs([approved_internal, draft_internal, approved_restricted])

    assert [document.id for document in kept] == ["KB-101"]


def test_004_filter_docs_handles_empty_input_and_keeps_scores() -> None:
    """[TEST-004][AC-008][DES-020][TASK-003] empty in, empty out; scores survive."""
    scored = replace(next(d for d in load_knowledge() if d.id == "KB-101"), score=7)

    assert filter_docs([]) == []
    assert filter_docs([scored])[0].score == 7
