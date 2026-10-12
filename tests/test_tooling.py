"""Tooling checks for TASK-001 (REQ-F-010, DES-018, DES-024)."""

from __future__ import annotations


def test_001_runtime_dependencies_import() -> None:
    """[TEST-001][REQ-F-010][TASK-001] approved runtime dependencies are importable."""
    from langchain.agents import create_agent
    from langchain_anthropic import ChatAnthropic
    from langgraph.graph import StateGraph

    import langsmith

    assert callable(create_agent)
    assert ChatAnthropic is not None
    assert StateGraph is not None
    assert langsmith is not None


def test_001_live_marker_is_registered(pytestconfig) -> None:
    """[TEST-001][DES-024][TASK-001] the `live` marker is declared for manual runs."""
    markers = pytestconfig.getini("markers")
    assert any(marker.startswith("live") for marker in markers)
