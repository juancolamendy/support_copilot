"""Output contract and LLM schema checks for TASK-002 (REQ-F-008, DES-012..014)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest
from pydantic import ValidationError

from support_copilot.copilot import handle_support_ticket
from support_copilot.tools import create_fixture_tools
from support_copilot.types import (
    Citation,
    DraftAnswer,
    SupportResult,
    SupportTicket,
    TicketDetails,
)

CONTRACT_FIELDS = [
    "status",
    "error_message",
    "escalate",
    "response",
    "citations",
    "confidence_score",
    "owner",
    "incident",
    "area",
    "notes",
]


def test_002_support_result_has_exactly_the_contract_fields() -> None:
    """[TEST-002][AC-013][REQ-F-008][DES-013][TASK-002] field set matches the SDD."""
    result = SupportResult(status="ok")

    assert [field.name for field in fields(result)] == CONTRACT_FIELDS


def test_002_support_result_defaults_describe_a_non_escalated_empty_result() -> None:
    """[TEST-002][AC-013][REQ-F-008][DES-013][TASK-002] defaults imply no answer."""
    result = SupportResult(status="ok")

    assert result.error_message is None
    assert result.escalate is False
    assert result.response is None
    assert result.citations == []
    assert result.confidence_score is None
    assert result.owner is None
    assert result.incident is None
    assert result.area is None
    assert result.notes == []


def test_002_support_result_defaults_are_not_shared_between_instances() -> None:
    """[TEST-002][AC-013][DES-013][TASK-002] mutable defaults are per instance."""
    first = SupportResult(status="ok")
    second = SupportResult(status="ok")

    first.notes.append("only on first")

    assert second.notes == []


def test_002_support_result_is_frozen() -> None:
    """[TEST-002][AC-013][DES-013][TASK-002] results are immutable."""
    result = SupportResult(status="ok")

    with pytest.raises(FrozenInstanceError):
        result.status = "error"  # type: ignore[misc]


def test_002_citation_carries_source_id_and_reason() -> None:
    """[TEST-002][AC-013][DES-013][TASK-002] Citation replaces Evidence."""
    citation = Citation(source_id="KB-101", reason="matched password reset")

    assert (citation.source_id, citation.reason) == ("KB-101", "matched password reset")


def test_002_ticket_details_requires_a_summary() -> None:
    """[TEST-002][AC-013][REQ-F-002][DES-012][TASK-002] a summary is required."""
    with pytest.raises(ValidationError):
        TicketDetails.model_validate({"symptoms": ["blank page"]})


def test_002_ticket_details_accepts_a_complete_payload() -> None:
    """[TEST-002][AC-013][REQ-F-002][DES-012][TASK-002] valid output parses."""
    details = TicketDetails.model_validate(
        {
            "summary": "Invitation expired",
            "symptoms": ["link no longer opens"],
            "product_terms": ["invitation", "portal"],
        }
    )

    assert details.product_terms == ["invitation", "portal"]


def test_002_draft_answer_requires_a_response() -> None:
    """[TEST-002][AC-013][REQ-F-007][DES-012][TASK-002] the draft carries only text."""
    with pytest.raises(ValidationError):
        DraftAnswer.model_validate({})

    assert [name for name in DraftAnswer.model_fields] == ["response"]


async def test_002_placeholder_handler_returns_an_error_result() -> None:
    """[TEST-002][AC-013][DES-013][TASK-002] repo still runs on the new contract."""
    ticket = SupportTicket(
        id="TCK-TEST",
        title="Any title",
        description="Any description",
        requester_role="Tester",
        created_at="2026-10-12T00:00:00Z",
    )

    result = await handle_support_ticket(ticket, create_fixture_tools())

    assert isinstance(result, SupportResult)
    assert result.status == "error"
    assert result.error_message
    assert result.escalate is False
    assert result.response is None
