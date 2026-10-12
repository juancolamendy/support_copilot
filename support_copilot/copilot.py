from __future__ import annotations

from .types import CopilotTools, SupportDecision, SupportTicket


async def handle_support_ticket(
    ticket: SupportTicket,
    tools: CopilotTools,
) -> SupportDecision:
    """Implement the Product Support Copilot here."""
    del ticket, tools

    return SupportDecision(
        action="escalate",
        message="The Product Support Copilot has not been implemented yet.",
        notes=["Starter implementation"],
    )
