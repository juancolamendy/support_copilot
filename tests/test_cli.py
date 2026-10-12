"""CLI checks for TASK-009 (REQ-F-001, REQ-NF-003, DES-005/015, AC-011/010/004)."""

from __future__ import annotations

import asyncio
import io
import json

import pytest

from support_copilot import demo
from support_copilot.cli import main
from support_copilot.types import SupportResult

SENTINEL = "sk-test-SENTINEL-key-value"
TERMS_1001 = ["patient portal", "password reset", "reset email"]
TERMS_1002 = ["portal invitation", "invitation expiration", "resend invitation"]


def _replies(structured_reply, product_terms, draft="Follow the article steps."):
    details = structured_reply(
        "TicketDetails",
        summary="Summary of the problem",
        symptoms=["it fails"],
        product_terms=product_terms,
    )
    return details, structured_reply("DraftAnswer", response=draft)


def _run(capsys, argv, model=None):
    code = main(argv, model=model)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_019_fixture_ticket_prints_one_json_result_and_exits_zero(
    capsys, make_fake_model, structured_reply
) -> None:
    """[TEST-019][AC-011][REQ-F-001][DES-005][TASK-009] --ticket TCK-1001."""
    model = make_fake_model(*_replies(structured_reply, TERMS_1001))

    code, out, _ = _run(capsys, ["--ticket", "TCK-1001"], model)

    result = json.loads(out)
    assert code == 0
    assert result["status"] == "ok"
    assert [citation["source_id"] for citation in result["citations"]] == ["KB-101"]


def test_019_confidence_is_rounded_for_display_only(
    capsys, make_fake_model, structured_reply
) -> None:
    """[TEST-019][AC-011][REQ-F-001][DES-005][TASK-009] 0.8333... prints as 0.83."""
    model = make_fake_model(*_replies(structured_reply, TERMS_1001))

    _, out, _ = _run(capsys, ["--ticket", "TCK-1001"], model)

    assert json.loads(out)["confidence_score"] == 0.83


def test_019_free_text_arguments_are_accepted(
    capsys, make_fake_model, structured_reply
) -> None:
    """[TEST-019][AC-011][REQ-F-001][DES-005][TASK-009] --title and --description."""
    model = make_fake_model(*_replies(structured_reply, TERMS_1002))
    argv = [
        "--title",
        "Portal invitation expired",
        "--description",
        "The invitation was sent two days ago and no longer opens.",
    ]

    code, out, _ = _run(capsys, argv, model)

    result = json.loads(out)
    assert code == 0
    assert [citation["source_id"] for citation in result["citations"]] == ["KB-103"]


def test_019_a_dash_description_is_read_from_stdin(
    capsys, monkeypatch, make_fake_model, structured_reply, prompt_text
) -> None:
    """[TEST-019][AC-011][REQ-F-001][DES-005][TASK-009] --description - uses stdin."""
    monkeypatch.setattr("sys.stdin", io.StringIO("The invitation no longer opens."))
    model = make_fake_model(*_replies(structured_reply, TERMS_1002))

    code, out, _ = _run(
        capsys, ["--title", "Portal invitation expired", "--description", "-"], model
    )

    assert code == 0
    assert json.loads(out)["status"] == "ok"
    assert "The invitation no longer opens." in prompt_text(model)


def test_019_a_known_incident_exits_zero(
    capsys, make_fake_model, structured_reply
) -> None:
    """[TEST-019][AC-011][REQ-F-001][DES-005][TASK-009] ok outcomes exit 0."""
    model = make_fake_model(*_replies(structured_reply, TERMS_1001))

    code, out, _ = _run(capsys, ["--ticket", "TCK-1003"], model)

    result = json.loads(out)
    assert code == 0
    assert result["incident"]["id"] == "INC-2041"
    assert result["response"] is None


def test_019_an_unknown_ticket_id_is_an_error_result_with_exit_one(
    capsys, make_fake_model
) -> None:
    """[TEST-019][AC-011][REQ-F-001][DES-005][TASK-009] unknown id: JSON error, 1."""
    code, out, _ = _run(capsys, ["--ticket", "TCK-9999"], make_fake_model())

    result = json.loads(out)
    assert code == 1
    assert result["status"] == "error"
    assert "TCK-9999" in result["error_message"]


@pytest.mark.parametrize(
    "argv",
    [
        ["--ticket", "TCK-1001", "--title", "Something"],
        ["--ticket", "TCK-1001", "--description", "Something"],
        [],
    ],
)
def test_019_invalid_argument_combinations_exit_two_without_stdout(
    capsys, make_fake_model, argv: list[str]
) -> None:
    """[TEST-019][AC-011][REQ-F-001][DES-005][TASK-009] usage errors exit 2."""
    code, out, err = _run(capsys, argv, make_fake_model())

    assert code == 2
    assert out == ""
    assert err


def test_019_stdout_is_a_single_json_object_and_logs_go_to_stderr(
    capsys, make_fake_model, structured_reply
) -> None:
    """[TEST-019][AC-011][REQ-NF-004][DES-023][TASK-009] diagnostics use stderr."""
    model = make_fake_model(*_replies(structured_reply, TERMS_1001))

    _, out, err = _run(capsys, ["--ticket", "TCK-1001"], model)

    assert isinstance(json.loads(out), dict)
    assert "node=" not in out
    assert "node=validate" in err
    assert "node=draft" in err


def test_020_no_path_prints_the_api_key(
    capsys, monkeypatch, make_fake_model, structured_reply
) -> None:
    """[TEST-020][AC-010][REQ-NF-003][DES-015][TASK-009] key absent from all output."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", SENTINEL)
    scenarios = [
        (["--ticket", "TCK-1001"], _replies(structured_reply, TERMS_1001)),
        (["--ticket", "TCK-1003"], _replies(structured_reply, TERMS_1001)),
        (["--ticket", "TCK-9999"], ()),
        (["--title", "Portal", "--description", " "], ()),
    ]

    for argv, replies in scenarios:
        _, out, err = _run(capsys, argv, make_fake_model(*replies))
        assert SENTINEL not in out
        assert SENTINEL not in err


def test_020_an_error_that_echoes_the_key_is_not_printed(
    capsys, monkeypatch
) -> None:
    """[TEST-020][AC-010][REQ-NF-003][DES-021][TASK-009] exception text stays hidden."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", SENTINEL)

    def failing_model():
        raise RuntimeError(f"rejected key {SENTINEL}")

    monkeypatch.setattr("support_copilot.workflow.get_model", failing_model)

    code, out, err = _run(capsys, ["--ticket", "TCK-1001"])

    assert code == 1
    assert json.loads(out)["status"] == "error"
    assert SENTINEL not in out
    assert SENTINEL not in err


def test_021_an_empty_description_exits_one_and_names_the_field(
    capsys, make_fake_model
) -> None:
    """[TEST-021][AC-004][REQ-F-003][DES-005][TASK-009] exit code mirrors status."""
    model = make_fake_model()

    code, out, _ = _run(capsys, ["--title", "Portal", "--description", ""], model)

    result = json.loads(out)
    assert code == 1
    assert result["status"] == "error"
    assert "description" in result["error_message"]
    assert model.calls == []


def test_019_the_demo_prints_every_fixture_ticket_with_the_same_formatting(
    capsys, monkeypatch
) -> None:
    """[TEST-019][REQ-F-001][DES-005][TASK-009] demo shares the CLI's JSON format."""

    async def stub(ticket, tools):
        return SupportResult(status="ok", confidence_score=0.8333333)

    monkeypatch.setattr(demo, "handle_support_ticket", stub)

    asyncio.run(demo.main())
    out = capsys.readouterr().out

    for ticket_id in ("TCK-1001", "TCK-1002", "TCK-1003"):
        assert ticket_id in out
    assert out.count('"confidence_score": 0.83') == 3
