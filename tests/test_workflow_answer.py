"""Workflow answer and escalate checks for TASK-008 (REQ-F-005..008)."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from support_copilot.copilot import handle_support_ticket
from support_copilot.fixture_store import load_tickets
from support_copilot.tools import FixtureTools
from support_copilot.types import KnowledgeDocument, SupportTicket

CONTRACT_FIELDS = {
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
}
# product_terms the real model returned on 2026-10-12 for the fixture tickets.
TERMS_1001 = ["patient portal", "password reset", "reset email"]
TERMS_1002 = ["portal invitation", "invitation expiration", "resend invitation"]
BILLING_TERMS = ["account balance", "billing adjustment"]


class RecordingTools(FixtureTools):
    """Fixture tools that remember which lookups the workflow made."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    async def search_knowledge(self, query, limit=5):
        self.calls.append("search_knowledge")
        return await super().search_knowledge(query, limit)

    async def find_active_incidents(self, area=None):
        self.calls.append("find_active_incidents")
        return await super().find_active_incidents(area)

    async def find_owner(self, area):
        self.calls.append("find_owner")
        return await super().find_owner(area)


def _fixture_ticket(ticket_id: str) -> SupportTicket:
    return next(ticket for ticket in load_tickets() if ticket.id == ticket_id)


def _billing_ticket() -> SupportTicket:
    return SupportTicket(
        id="TCK-BILL",
        title="Account balance question",
        description="Adjust an account balance on a billing statement",
        requester_role="Billing Specialist",
        created_at="2026-10-12T00:00:00Z",
    )


def _replies(structured_reply, product_terms, draft="Follow the article steps."):
    details = structured_reply(
        "TicketDetails",
        summary="Summary of the problem",
        symptoms=["it fails"],
        product_terms=product_terms,
    )
    return details, structured_reply("DraftAnswer", response=draft)


async def test_013_answerable_ticket_gets_a_cited_draft(
    make_fake_model, structured_reply
) -> None:
    """[TEST-013][AC-001][REQ-F-007][DES-010][TASK-008] TCK-1001 is answered."""
    model = make_fake_model(*_replies(structured_reply, TERMS_1001, "Open the email."))

    result = await handle_support_ticket(
        _fixture_ticket("TCK-1001"), RecordingTools(), model
    )

    assert result.status == "ok"
    assert result.escalate is False
    assert result.response == "Open the email."
    assert [citation.source_id for citation in result.citations] == ["KB-101"]
    assert result.confidence_score is not None and result.confidence_score >= 0.70
    assert result.incident is None
    assert len(model.calls) == 2


async def test_013_the_model_cannot_add_citations(
    make_fake_model, structured_reply
) -> None:
    """[TEST-013][AC-001][REQ-F-007][DES-011][TASK-008] text mentions do not cite."""
    replies = _replies(structured_reply, TERMS_1001, "See [KB-999] and KB-103.")
    model = make_fake_model(*replies)

    result = await handle_support_ticket(
        _fixture_ticket("TCK-1001"), RecordingTools(), model
    )

    assert [citation.source_id for citation in result.citations] == ["KB-101"]


async def test_014_deprecated_document_is_never_cited_or_sent_to_the_model(
    make_fake_model, structured_reply, prompt_text
) -> None:
    """[TEST-014][AC-002][REQ-F-005][DES-028][TASK-008] KB-103 yes, KB-102 never."""
    model = make_fake_model(*_replies(structured_reply, TERMS_1002))

    result = await handle_support_ticket(
        _fixture_ticket("TCK-1002"), RecordingTools(), model
    )

    assert result.status == "ok"
    assert [citation.source_id for citation in result.citations] == ["KB-103"]
    sent = prompt_text(model)
    assert "[KB-102]" not in sent
    assert "24 hours" in sent


async def test_015_no_approved_document_escalates_without_drafting(
    make_fake_model, structured_reply, capsys
) -> None:
    """[TEST-015][AC-006][REQ-F-006][DES-010][TASK-008] restricted KB-105 is ignored."""
    tools = RecordingTools()
    model = make_fake_model(*_replies(structured_reply, BILLING_TERMS))

    result = await handle_support_ticket(_billing_ticket(), tools, model)

    assert result.escalate is True
    assert result.status == "ok"
    assert result.response is None
    assert result.citations == []
    assert result.area == "billing"
    assert result.owner is not None
    assert result.owner.team == "Revenue Cycle Operations"
    assert result.owner.escalation_channel == "#help-revenue-cycle"
    assert len(model.calls) == 1
    printed = capsys.readouterr().err
    assert "Revenue Cycle Operations" in printed
    assert "billing" in printed
    assert "#help-revenue-cycle" in printed


@pytest.mark.parametrize("scenario", ["error", "incident", "escalation", "answer"])
async def test_016_every_outcome_returns_the_full_contract(
    make_fake_model, structured_reply, scenario: str
) -> None:
    """[TEST-016][AC-013][REQ-F-008][DES-013][TASK-008] same fields on every path."""
    ticket, terms = {
        "error": (_fixture_ticket("TCK-1001"), TERMS_1001),
        "incident": (_fixture_ticket("TCK-1003"), TERMS_1001),
        "escalation": (_billing_ticket(), BILLING_TERMS),
        "answer": (_fixture_ticket("TCK-1001"), TERMS_1001),
    }[scenario]
    if scenario == "error":
        ticket = SupportTicket("TCK-E", "Portal", " ", "Tester", "2026-10-12")
    model = make_fake_model(*_replies(structured_reply, terms))

    result = await handle_support_ticket(ticket, RecordingTools(), model)

    assert set(asdict(result)) == CONTRACT_FIELDS
    assert result.status == ("error" if scenario == "error" else "ok")
    assert (result.response is not None) is (scenario == "answer")
    assert result.escalate is (scenario == "escalation")
    assert (result.incident is not None) is (scenario == "incident")


async def test_018_low_confidence_escalates_without_drafting(
    make_fake_model, structured_reply
) -> None:
    """[TEST-018][AC-007][REQ-F-006a][DES-027][TASK-008] below 0.70 escalates."""
    diluted = ["zzzzz", "qqqqq", "wwwww"]
    model = make_fake_model(*_replies(structured_reply, diluted))

    result = await handle_support_ticket(
        _fixture_ticket("TCK-1001"), RecordingTools(), model
    )

    assert result.escalate is True
    assert result.response is None
    assert result.confidence_score is not None and result.confidence_score < 0.70
    assert len(model.calls) == 1


async def test_018_a_score_of_exactly_the_threshold_still_answers(
    make_fake_model, structured_reply
) -> None:
    """[TEST-018][AC-007][REQ-F-006a][DES-027][TASK-008] 0.70 is not below 0.70."""
    document = KnowledgeDocument(
        id="KB-EDGE",
        title="Edge",
        content="portal alpha bravo charlie delta echoes foxtrot",
        source="test",
        owner="Portal Platform",
        last_updated="2026-10-12",
        status="approved",
        access="internal",
        score=9,
    )

    class EdgeTools(RecordingTools):
        async def search_knowledge(self, query, limit=5):
            return [document]

    ticket = SupportTicket(
        "TCK-EDGE",
        "Portal alpha bravo charlie delta echoes foxtrot",
        "Something about the portal",
        "Tester",
        "2026-10-12",
    )
    model = make_fake_model(*_replies(structured_reply, ["golf hotel india"]))

    result = await handle_support_ticket(ticket, EdgeTools(), model)

    assert result.confidence_score == pytest.approx(0.70)
    assert result.escalate is False
    assert result.response is not None
