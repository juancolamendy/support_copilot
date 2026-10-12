"""Fixture tool wrapper checks for TASK-005 (REQ-F-009, DES-007)."""

from __future__ import annotations

import pytest

from support_copilot.tools import build_langchain_tools, create_fixture_tools

TOOL_NAMES = {"get_ticket", "find_active_incidents", "search_knowledge", "find_owner"}


@pytest.fixture
def tools_by_name() -> dict:
    return {tool.name: tool for tool in build_langchain_tools(create_fixture_tools())}


def test_007_exposes_one_tool_per_fixture(tools_by_name: dict) -> None:
    """[TEST-007][AC-014][REQ-F-009][DES-007][TASK-005] one tool per fixture."""
    assert set(tools_by_name) == TOOL_NAMES


def test_007_every_tool_describes_itself_to_the_model(tools_by_name: dict) -> None:
    """[TEST-007][AC-014][REQ-F-009][DES-007][TASK-005] description and arguments."""
    for tool in tools_by_name.values():
        assert tool.description
        assert tool.args


async def test_007_incident_tool_returns_the_active_scheduling_incident(
    tools_by_name: dict,
) -> None:
    """[TEST-007][AC-014][REQ-F-009][DES-007][TASK-005] INC-2041 for scheduling."""
    incidents = await tools_by_name["find_active_incidents"].ainvoke(
        {"area": "scheduling"}
    )

    assert [incident["id"] for incident in incidents] == ["INC-2041"]


async def test_007_incident_tool_leaves_out_resolved_incidents(
    tools_by_name: dict,
) -> None:
    """[TEST-007][AC-014][REQ-F-009][DES-007][TASK-005] INC-2022 is resolved."""
    incidents = await tools_by_name["find_active_incidents"].ainvoke(
        {"area": "patient-portal"}
    )

    assert incidents == []


async def test_007_knowledge_tool_finds_the_invitation_document(
    tools_by_name: dict,
) -> None:
    """[TEST-007][AC-014][REQ-F-009][DES-007][TASK-005] KB-103 for an invitation."""
    documents = await tools_by_name["search_knowledge"].ainvoke(
        {"query": "expired portal invitation"}
    )

    assert "KB-103" in [document["id"] for document in documents]


async def test_007_owner_tool_returns_the_portal_team(tools_by_name: dict) -> None:
    """[TEST-007][AC-014][REQ-F-009][DES-007][TASK-005] Portal Platform owns it."""
    owner = await tools_by_name["find_owner"].ainvoke({"area": "patient-portal"})

    assert owner["team"] == "Portal Platform"
    assert owner["escalation_channel"] == "#help-portal-platform"


async def test_007_ticket_tool_returns_the_fixture_ticket(
    tools_by_name: dict,
) -> None:
    """[TEST-007][AC-014][REQ-F-009][DES-007][TASK-005] TCK-1001 by id."""
    ticket = await tools_by_name["get_ticket"].ainvoke({"ticket_id": "TCK-1001"})

    assert ticket["id"] == "TCK-1001"
    assert ticket["title"] == "Patient cannot reset portal password"


async def test_007_unknown_ticket_returns_an_error_value_not_an_exception(
    tools_by_name: dict,
) -> None:
    """[TEST-007][AC-014][REQ-F-009][DES-007][TASK-005] a miss is data, not a crash."""
    result = await tools_by_name["get_ticket"].ainvoke({"ticket_id": "TCK-9999"})

    assert result == {"error": "ticket not found: TCK-9999"}


async def test_007_unknown_owner_area_returns_an_error_value(
    tools_by_name: dict,
) -> None:
    """[TEST-007][AC-014][REQ-F-009][DES-007][TASK-005] no owner is reported."""
    result = await tools_by_name["find_owner"].ainvoke({"area": "no-such-area"})

    assert result == {"error": "no owner found for area: no-such-area"}
