from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

from .copilot import handle_support_ticket
from .fixture_store import load_tickets
from .tools import create_fixture_tools


async def main() -> None:
    for ticket in load_tickets():
        result = await handle_support_ticket(ticket, create_fixture_tools())
        print(f"\n{ticket.id}: {ticket.title}")
        print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
