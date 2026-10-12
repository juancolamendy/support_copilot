"""Shared test doubles for the offline suite (DES-024)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class FakeChatModel(BaseChatModel):
    """Deterministic chat model: replays canned replies and records every call.

    A reply is an `AIMessage` or an exception to raise. `bind_tools` returns the
    model itself so `create_agent` can use it for structured output.
    """

    responses: list[Any] = Field(default_factory=list)
    calls: list[list[BaseMessage]] = Field(default_factory=list)
    delay: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"

    def _reply(self) -> ChatResult:
        reply = self.responses.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(generations=[ChatGeneration(message=reply)])

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(messages)
        return self._reply()

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(messages)
        if self.delay:
            await asyncio.sleep(self.delay)
        return self._reply()

    def bind_tools(self, tools, **kwargs):
        return self


@pytest.fixture
def structured_reply() -> Callable[..., AIMessage]:
    """Build the reply a model gives when it fills a structured-output schema."""

    def build(schema_name: str, **args: Any) -> AIMessage:
        call = {"name": schema_name, "args": args, "id": "call-1", "type": "tool_call"}
        return AIMessage(content="", tool_calls=[call])

    return build


@pytest.fixture
def make_fake_model() -> Callable[..., FakeChatModel]:
    def make(*responses: Any, delay: float = 0.0) -> FakeChatModel:
        return FakeChatModel(responses=list(responses), delay=delay)

    return make


@pytest.fixture
def prompt_text() -> Callable[[FakeChatModel], str]:
    """All message text the fake model received, joined for assertions."""

    def text(model: FakeChatModel) -> str:
        return "\n".join(str(m.content) for call in model.calls for m in call)

    return text
