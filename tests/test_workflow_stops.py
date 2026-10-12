"""Workflow early-stop checks for TASK-007 (REQ-F-003/003a/004, DES-002/003/004/010)."""

from __future__ import annotations

import logging

import pytest

from support_copilot.copilot import handle_support_ticket
from support_copilot.fixture_store import load_tickets
from support_copilot.tools import FixtureTools
from support_copilot.types import Incident, SupportTicket

DETAILS = {"summary": "Short summary", "symptoms": ["it fails"], "product_terms": ["x"]}


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


def _ticket(title: str, description: str) -> SupportTicket:
    return SupportTicket(
        id="TCK-TEST",
        title=title,
        description=description,
        requester_role="Tester",
        created_at="2026-10-12T00:00:00Z",
    )


async def test_010_known_incident_stops_the_flow_with_incident_and_owner(
    make_fake_model, structured_reply
) -> None:
    """[TEST-010][AC-003][REQ-F-004][DES-010][TASK-007] TCK-1003 stops at INC-2041."""
    tools = RecordingTools()
    model = make_fake_model(structured_reply("TicketDetails", **DETAILS))

    result = await handle_support_ticket(_fixture_ticket("TCK-1003"), tools, model)

    assert result.status == "ok"
    assert result.escalate is False
    assert result.response is None
    assert result.area == "scheduling"
    assert result.incident is not None and result.incident.id == "INC-2041"
    assert result.owner is not None
    assert result.owner.team == "Care Access Engineering"
    assert result.owner.escalation_channel == "#help-care-access"


async def test_010_incident_stop_makes_no_search_and_no_drafting_call(
    make_fake_model, structured_reply
) -> None:
    """[TEST-010][AC-003][REQ-F-004][DES-009][TASK-007] only extraction uses the LLM."""
    tools = RecordingTools()
    model = make_fake_model(structured_reply("TicketDetails", **DETAILS))

    await handle_support_ticket(_fixture_ticket("TCK-1003"), tools, model)

    assert "search_knowledge" not in tools.calls
    assert len(model.calls) == 1


async def test_010_resolved_incidents_do_not_stop_the_flow(
    make_fake_model, structured_reply
) -> None:
    """[TEST-010][AC-003][REQ-F-004][DES-010][TASK-007] INC-2022 is resolved."""
    tools = RecordingTools()
    model = make_fake_model(structured_reply("TicketDetails", **DETAILS))

    result = await handle_support_ticket(_fixture_ticket("TCK-1001"), tools, model)

    assert "find_active_incidents" in tools.calls
    assert result.incident is None


async def test_010_the_most_recently_updated_incident_is_reported(
    make_fake_model, structured_reply
) -> None:
    """[TEST-010][AC-003][REQ-F-004][DES-010][TASK-007] newest active incident wins."""

    class TwoIncidents(RecordingTools):
        async def find_active_incidents(self, area=None):
            await super().find_active_incidents(area)
            return [
                Incident("INC-OLD", "scheduling", "investigating", "old", "2026-09-01"),
                Incident("INC-NEW", "scheduling", "identified", "new", "2026-09-30"),
            ]

    model = make_fake_model(structured_reply("TicketDetails", **DETAILS))

    result = await handle_support_ticket(
        _fixture_ticket("TCK-1003"), TwoIncidents(), model
    )

    assert result.incident is not None and result.incident.id == "INC-NEW"


async def test_010_each_node_logs_one_line_without_ticket_text(
    make_fake_model, structured_reply, caplog
) -> None:
    """[TEST-010][REQ-NF-004][DES-023][TASK-007] node logs carry no ticket text."""
    ticket = _fixture_ticket("TCK-1003")
    model = make_fake_model(structured_reply("TicketDetails", **DETAILS))

    with caplog.at_level(logging.INFO, logger="support_copilot.workflow"):
        await handle_support_ticket(ticket, RecordingTools(), model)

    messages = [record.getMessage() for record in caplog.records]
    for node in ("validate", "extract", "detect_area", "check_incident"):
        assert sum(f"node={node} " in message for message in messages) == 1
    assert any("node=check_incident outcome=stop" in m for m in messages)
    assert all(ticket.title not in m and ticket.description not in m for m in messages)


@pytest.mark.parametrize("description", ["", "   ", "\n\t"])
async def test_011_missing_description_stops_before_the_model(
    make_fake_model, description: str
) -> None:
    """[TEST-011][AC-004][REQ-F-003][DES-030][TASK-007] no description, no LLM call."""
    tools = RecordingTools()
    model = make_fake_model()

    result = await handle_support_ticket(
        _ticket("Portal invitation", description), tools, model
    )

    assert result.status == "error"
    assert result.error_message and "description" in result.error_message
    assert result.escalate is False
    assert result.response is None
    assert model.calls == []
    assert tools.calls == []


async def test_012_unknown_area_stops_before_incident_and_owner_lookups(
    make_fake_model, structured_reply
) -> None:
    """[TEST-012][AC-005][REQ-F-003a][DES-004][TASK-007] no area, no lookups."""
    tools = RecordingTools()
    model = make_fake_model(structured_reply("TicketDetails", **DETAILS))

    result = await handle_support_ticket(
        _ticket("Printer jam", "The office printer keeps jamming"), tools, model
    )

    assert result.status == "error"
    assert result.error_message and "area" in result.error_message
    assert result.escalate is False
    assert result.response is None
    assert tools.calls == []
