"""Live checks for TASK-010 (REQ-NF-001, REQ-NF-004, DES-019, DES-023).

These call the real Anthropic API (and LangSmith for the trace check), so they run
only on request:  uv run pytest -m live -s
COPILOT_LIVE_RUNS sets the runs per fixture ticket (default 20).
"""

from __future__ import annotations

import asyncio
import math
import os
import time
import uuid

import pytest

from support_copilot.copilot import handle_support_ticket
from support_copilot.fixture_store import load_tickets
from support_copilot.tools import create_fixture_tools

pytestmark = pytest.mark.live

RUNS_PER_TICKET = int(os.environ.get("COPILOT_LIVE_RUNS", "20"))
LATENCY_BUDGET_SECONDS = 10.0


@pytest.fixture(autouse=True)
def _live_opt_in(request: pytest.FixtureRequest) -> None:
    if "live" not in (request.config.getoption("markexpr") or ""):
        pytest.skip("live tests run only with `-m live`")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY is not set")


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


async def test_022_p95_latency_is_within_the_budget() -> None:
    """[TEST-022][AC-009][REQ-NF-001][DES-019][TASK-010] 3 fixtures x N live runs."""
    timings: dict[str, list[float]] = {}
    for ticket in load_tickets():
        for _ in range(RUNS_PER_TICKET):
            started = time.perf_counter()
            result = await handle_support_ticket(ticket, create_fixture_tools())
            timings.setdefault(ticket.id, []).append(time.perf_counter() - started)
            assert result.status == "ok", f"{ticket.id}: {result.error_message}"

    for ticket_id, values in timings.items():
        stats = f"runs={len(values)} p95={_p95(values):.2f}s max={max(values):.2f}s"
        print(f"{ticket_id}: {stats}")
    overall = _p95([value for values in timings.values() for value in values])
    print(f"overall p95={overall:.2f}s budget={LATENCY_BUDGET_SECONDS:.0f}s")

    assert overall <= LATENCY_BUDGET_SECONDS


async def test_024_a_run_creates_a_langsmith_trace_and_prints_no_key(capsys) -> None:
    """[TEST-024][AC-010][REQ-NF-004][DES-023][TASK-010] trace exists, key absent."""
    from langchain_core.tracers.context import tracing_v2_enabled
    from langchain_core.tracers.langchain import wait_for_all_tracers
    from langsmith import Client

    langsmith_key = os.environ.get("LANGSMITH_API_KEY")
    if not langsmith_key:
        pytest.skip("LANGSMITH_API_KEY is not set")
    project = f"support-copilot-live-{uuid.uuid4().hex[:8]}"
    ticket = next(t for t in load_tickets() if t.id == "TCK-1002")
    client = Client()

    try:
        with tracing_v2_enabled(project_name=project):
            await handle_support_ticket(ticket, create_fixture_tools())
        wait_for_all_tracers()
        runs = []
        for _ in range(15):
            runs = list(client.list_runs(project_name=project, limit=5))
            if runs:
                break
            await asyncio.sleep(2)
    finally:
        try:
            client.delete_project(project_name=project)
        except Exception:  # noqa: BLE001 - cleanup must not hide the result
            pass

    captured = capsys.readouterr()
    assert runs, f"no trace appeared in LangSmith project {project}"
    for secret in (langsmith_key, os.environ["ANTHROPIC_API_KEY"]):
        assert secret not in captured.out
        assert secret not in captured.err
