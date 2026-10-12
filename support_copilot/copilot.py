from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from .types import CopilotTools, SupportResult, SupportTicket
from .workflow import build_workflow


async def handle_support_ticket(
    ticket: SupportTicket,
    tools: CopilotTools,
    model: BaseChatModel | None = None,
) -> SupportResult:
    """Run one ticket through the support workflow.

    `model` is created from the environment when omitted; tests inject a fake.
    """
    state = await build_workflow(tools, model).ainvoke({"ticket": ticket})
    return state["result"]
