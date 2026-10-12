from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, TypedDict

from pydantic import BaseModel, Field

AccessLevel = Literal["internal", "restricted"]
DocumentStatus = Literal["approved", "draft", "deprecated"]
IncidentStatus = Literal["investigating", "identified", "monitoring", "resolved"]
ResultStatus = Literal["ok", "error"]


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
class Citation:
    source_id: str
    reason: str


@dataclass(frozen=True)
class SupportResult:
    status: ResultStatus
    error_message: str | None = None
    escalate: bool = False
    response: str | None = None
    citations: list[Citation] = field(default_factory=list)
    confidence_score: float | None = None
    owner: ServiceOwner | None = None
    incident: Incident | None = None
    area: str | None = None
    notes: list[str] = field(default_factory=list)


class TicketDetails(BaseModel):
    """Structured output of the extraction step."""

    summary: str
    symptoms: list[str] = Field(default_factory=list)
    product_terms: list[str] = Field(default_factory=list)


class DraftAnswer(BaseModel):
    """Structured output of the drafting step; citations are never model-set."""

    response: str


class WorkflowState(TypedDict, total=False):
    """Per-run state of the support workflow; never persisted."""

    ticket: SupportTicket
    details: TicketDetails
    area: str | None
    incident: Incident | None
    documents: list[KnowledgeDocument]
    confidence_score: float | None
    response: str | None
    result: SupportResult


class CopilotTools(Protocol):
    model: LanguageModel

    async def search_knowledge(
        self, query: str, limit: int = 5
    ) -> list[KnowledgeDocument]: ...

    async def find_owner(self, area: str) -> ServiceOwner | None: ...

    async def find_active_incidents(self, area: str | None = None) -> list[Incident]: ...
