"""Command-line entry point: one stateless ticket per run (DES-005).

stdout carries exactly one JSON result; logs and usage errors go to stderr.
Exit code: 0 for an ok result, 1 for an error result, 2 for bad arguments.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Sequence
from dataclasses import asdict

from langchain_core.language_models.chat_models import BaseChatModel

from .copilot import handle_support_ticket
from .fixture_store import load_tickets
from .tools import create_fixture_tools
from .types import CopilotTools, SupportResult, SupportTicket


def format_result(result: SupportResult) -> str:
    """JSON for display; the score is rounded here and never in the gate."""
    data = asdict(result)
    if data["confidence_score"] is not None:
        data["confidence_score"] = round(data["confidence_score"], 2)
    return json.dumps(data, indent=2)


class _StderrHandler(logging.StreamHandler):
    """Writes to whatever `sys.stderr` is at emit time."""

    def __init__(self) -> None:
        super().__init__()

    @property
    def stream(self):  # type: ignore[override]
        return sys.stderr

    @stream.setter
    def stream(self, value) -> None:
        pass


def _configure_logging() -> None:
    logger = logging.getLogger("support_copilot")
    if not any(isinstance(handler, _StderrHandler) for handler in logger.handlers):
        handler = _StderrHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m support_copilot.cli",
        description="Triage one support ticket and print a JSON result.",
    )
    parser.add_argument("--ticket", help="id of a fixture ticket, e.g. TCK-1001")
    parser.add_argument("--title", help="ticket title (free text)")
    parser.add_argument("--description", help="ticket description; '-' reads stdin")
    parser.add_argument("--requester-role", default="unknown")
    parser.add_argument("--created-at", default="unknown")
    args = parser.parse_args(argv)
    if args.ticket is not None and (args.title or args.description is not None):
        parser.error("--ticket cannot be combined with --title or --description")
    if args.ticket is None and args.description is None:
        parser.error("provide --ticket, or --description (with optional --title)")
    return args


def _build_ticket(args: argparse.Namespace) -> SupportTicket | None:
    if args.ticket is not None:
        return next((t for t in load_tickets() if t.id == args.ticket), None)
    description = sys.stdin.read() if args.description == "-" else args.description
    return SupportTicket(
        id="TCK-CLI",
        title=args.title or "",
        description=description,
        requester_role=args.requester_role,
        created_at=args.created_at,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    tools: CopilotTools | None = None,
    model: BaseChatModel | None = None,
) -> int:
    """Run one ticket; `tools` and `model` are injected by tests."""
    try:
        args = _parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    _configure_logging()
    ticket = _build_ticket(args)
    if ticket is None:
        result = SupportResult(
            status="error", error_message=f"ticket not found: {args.ticket}"
        )
    else:
        result = asyncio.run(
            handle_support_ticket(ticket, tools or create_fixture_tools(), model)
        )
    print(format_result(result))
    return 0 if result.status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
