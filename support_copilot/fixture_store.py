from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import Incident, KnowledgeDocument, ServiceOwner, SupportTicket

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _read_fixture(filename: str) -> list[dict[str, Any]]:
    with (FIXTURES / filename).open(encoding="utf-8") as fixture:
        return json.load(fixture)


def load_tickets() -> list[SupportTicket]:
    return [
        SupportTicket(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            requester_role=row["requesterRole"],
            created_at=row["createdAt"],
        )
        for row in _read_fixture("tickets.json")
    ]


def load_knowledge() -> list[KnowledgeDocument]:
    return [
        KnowledgeDocument(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            source=row["source"],
            owner=row["owner"],
            last_updated=row["lastUpdated"],
            status=row["status"],
            access=row["access"],
        )
        for row in _read_fixture("knowledge.json")
    ]


def load_owners() -> list[ServiceOwner]:
    return [
        ServiceOwner(
            area=row["area"],
            team=row["team"],
            escalation_channel=row["escalationChannel"],
        )
        for row in _read_fixture("ownership.json")
    ]


def load_incidents() -> list[Incident]:
    return [
        Incident(
            id=row["id"],
            area=row["area"],
            status=row["status"],
            summary=row["summary"],
            updated_at=row["updatedAt"],
        )
        for row in _read_fixture("incidents.json")
    ]
