from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

AccessLevel = Literal["internal", "restricted"]
DocumentStatus = Literal["approved", "draft", "deprecated"]
IncidentStatus = Literal["investigating", "identified", "monitoring", "resolved"]
SupportAction = Literal["respond", "clarify", "escalate"]


@dataclass(frozen=True)
class SupportTicket:
    id: str
    title: str
    description: str
    requester_role: str
    created_at: str


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    title: str
    content: str
    source: str
    owner: str
    last_updated: str
    status: DocumentStatus
    access: AccessLevel
    score: int = 0


@dataclass(frozen=True)
class ServiceOwner:
    area: str
    team: str
    escalation_channel: str


@dataclass(frozen=True)
class Incident:
    id: str
    area: str
    status: IncidentStatus
    summary: str
    updated_at: str


@dataclass(frozen=True)
class ModelResponse:
    text: str
    model: str
    input_characters: int


class LanguageModel(Protocol):
    async def generate(self, system: str, prompt: str) -> ModelResponse: ...


@dataclass(frozen=True)
class Evidence:
    source_id: str
    reason: str


@dataclass(frozen=True)
class SupportDecision:
    action: SupportAction
    message: str
    evidence: list[Evidence] = field(default_factory=list)
    owner: ServiceOwner | None = None
    notes: list[str] = field(default_factory=list)


class CopilotTools(Protocol):
    model: LanguageModel

    async def search_knowledge(
        self, query: str, limit: int = 5
    ) -> list[KnowledgeDocument]: ...

    async def find_owner(self, area: str) -> ServiceOwner | None: ...

    async def find_active_incidents(self, area: str | None = None) -> list[Incident]: ...
