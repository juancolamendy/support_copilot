from __future__ import annotations

import asyncio
import unittest

from support_copilot.fixture_store import load_tickets
from support_copilot.tools import create_fixture_tools


class StarterTests(unittest.TestCase):
    def test_starter_fixtures_can_be_loaded(self) -> None:
        tickets = load_tickets()
        self.assertGreaterEqual(len(tickets), 3)
        self.assertTrue(all(ticket.id and ticket.description for ticket in tickets))

    def test_mock_tools_are_available(self) -> None:
        async def exercise_tools() -> None:
            tools = create_fixture_tools()
            hits = await tools.search_knowledge("expired portal invitation")
            incidents = await tools.find_active_incidents("scheduling")
            owner = await tools.find_owner("patient-portal")

            self.assertTrue(any(hit.id == "KB-103" for hit in hits))
            self.assertEqual(incidents[0].id, "INC-2041")
            self.assertEqual(owner.team if owner else None, "Portal Platform")

        asyncio.run(exercise_tools())


if __name__ == "__main__":
    unittest.main()
