from __future__ import annotations

from .types import CopilotTools, SupportResult, SupportTicket


async def handle_support_ticket(
    ticket: SupportTicket,
    tools: CopilotTools,
) -> SupportResult:
    """Implement the Product Support Copilot here."""
    del ticket, tools

    return SupportResult(
        status="error",
        error_message="The Product Support Copilot workflow is not implemented yet.",
        notes=["Placeholder until the workflow phases land"],
    )
