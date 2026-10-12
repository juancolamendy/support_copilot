"""Workflow failure-injection checks for TASK-008 (REQ-NF-002, DES-021, AC-015)."""

from __future__ import annotations

import logging

import pytest

from support_copilot.copilot import handle_support_ticket
from support_copilot.fixture_store import load_tickets
from support_copilot.tools import FixtureTools
from support_copilot.types import SupportTicket

SECRET = "sk-test-SECRET-value"
TERMS = ["patient portal", "password reset", "reset email"]


class FailingTools(FixtureTools):
    """Fixture tools where one named lookup raises an error carrying a secret."""

    def __init__(self, fail_on: str) -> None:
        super().__init__()
        self.fail_on = fail_on

    async def search_knowledge(self, query, limit=5):
        self._maybe_fail("search_knowledge")
        return await super().search_knowledge(query, limit)

    async def find_active_incidents(self, area=None):
        self._maybe_fail("find_active_incidents")
        return await super().find_active_incidents(area)

    async def find_owner(self, area):
        self._maybe_fail("find_owner")
        return await super().find_owner(area)

    def _maybe_fail(self, name: str) -> None:
        if name == self.fail_on:
            raise RuntimeError(f"{SECRET} lookup exploded")


def _ticket() -> SupportTicket:
    return next(ticket for ticket in load_tickets() if ticket.id == "TCK-1001")


def _billing_ticket() -> SupportTicket:
    return SupportTicket(
        id="TCK-BILL",
        title="Account balance question",
        description="Adjust an account balance on a billing statement",
        requester_role="Billing Specialist",
        created_at="2026-10-12T00:00:00Z",
    )


def _details(structured_reply, terms):
    return structured_reply(
        "TicketDetails", summary="Summary", symptoms=["it fails"], product_terms=terms
    )


def _assert_safe_error(result, *ticket_texts: str, step: str = "") -> None:
    assert result.status == "error"
    assert result.error_message
    assert step in result.error_message
    assert result.response is None
    assert result.escalate is False
    assert "Traceback" not in result.error_message
    assert SECRET not in result.error_message
    for text in ticket_texts:
        assert text not in result.error_message


async def test_017_extraction_failure_returns_an_error_result(
    make_fake_model,
) -> None:
    """[TEST-017][AC-015][REQ-NF-002][DES-021][TASK-008] model fails at extraction."""
    model = make_fake_model(RuntimeError(f"{SECRET} {_ticket().description}"))

    result = await handle_support_ticket(_ticket(), FixtureTools(), model)

    _assert_safe_error(result, _ticket().description)


@pytest.mark.parametrize(
    ("failing", "step"),
    [("find_active_incidents", "check_incident"), ("search_knowledge", "search")],
)
async def test_017_tool_failure_returns_an_error_result(
    make_fake_model, structured_reply, failing: str, step: str
) -> None:
    """[TEST-017][AC-015][REQ-NF-002][DES-021][TASK-008] a lookup raises."""
    model = make_fake_model(_details(structured_reply, TERMS))

    result = await handle_support_ticket(_ticket(), FailingTools(failing), model)

    _assert_safe_error(result, _ticket().description, step=step)
    assert "RuntimeError" in result.error_message


async def test_017_owner_lookup_failure_during_escalation_returns_an_error_result(
    make_fake_model, structured_reply
) -> None:
    """[TEST-017][AC-015][REQ-NF-002][DES-021][TASK-008] escalation lookup raises."""
    model = make_fake_model(_details(structured_reply, ["account balance"]))

    result = await handle_support_ticket(
        _billing_ticket(), FailingTools("find_owner"), model
    )

    _assert_safe_error(result, step="escalate")


async def test_017_drafting_failure_returns_an_error_result(
    make_fake_model, structured_reply
) -> None:
    """[TEST-017][AC-015][REQ-NF-002][DES-021][TASK-008] model fails at drafting."""
    model = make_fake_model(
        _details(structured_reply, TERMS),
        RuntimeError(f"{SECRET} {_ticket().description}"),
    )

    result = await handle_support_ticket(_ticket(), FixtureTools(), model)

    _assert_safe_error(result, _ticket().description)
    assert len(model.calls) == 2


async def test_017_a_missing_api_key_returns_an_error_result_not_an_exception(
    monkeypatch,
) -> None:
    """[TEST-017][AC-015][REQ-NF-002][DES-021][TASK-008] no key, no model, no crash."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = await handle_support_ticket(_ticket(), FixtureTools())

    _assert_safe_error(result, _ticket().description)


async def test_017_a_failed_node_logs_its_name_and_error_class_but_no_text(
    make_fake_model, structured_reply, caplog
) -> None:
    """[TEST-017][AC-015][REQ-NF-004][DES-023][TASK-008] debuggable, not leaky."""
    model = make_fake_model(_details(structured_reply, TERMS))

    with caplog.at_level(logging.INFO, logger="support_copilot.workflow"):
        await handle_support_ticket(_ticket(), FailingTools("search_knowledge"), model)

    messages = [record.getMessage() for record in caplog.records]
    assert any("node=search outcome=error error=RuntimeError" in m for m in messages)
    assert all(SECRET not in m for m in messages)
    assert all(_ticket().description not in m for m in messages)
