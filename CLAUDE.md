# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Context

This is the Python implementation of a Talkiatry interview exercise: a **Product Support Copilot** that takes a Jira-style support ticket and helps a support expert decide how to handle it. For each ticket it returns one of: a cited draft reply, an error naming missing data, a stop at a known incident, or an escalation to the owning team. The task statement is in `../README.md`; the requirements, design and plan are in `docs/requirement/`, `docs/design/` and `docs/plan/`. Interview material is confidential and all data is synthetic (see `../NOTICE.md`). The sibling `../typescript/` directory is an equivalent starter and is not used.

## Commands

Run from this `python/` directory through uv (the system `python3` may be older than the required 3.11).

```bash
uv sync                                                       # install runtime and dev dependencies
uv run pytest                                                 # all tests: offline, deterministic, no API calls
uv run pytest tests/test_workflow_answer.py::test_013_answerable_ticket_gets_a_cited_draft   # single test
uv run pytest tests/test_traceability.py                      # fails if an AC has no test naming it
uv run pytest -m live -s                                      # opt-in live checks: real Anthropic (+ LangSmith)
uv run python -m support_copilot.cli --ticket TCK-1001        # one fixture ticket; or --title/--description
uv run python -m support_copilot.demo                         # every fixture ticket (real model if a key is set)
```

Live runs need `ANTHROPIC_API_KEY` (model from `COPILOT_MODEL`, default `claude-sonnet-5-5`); the trace check also needs `LANGSMITH_API_KEY`. Plain `uv run pytest` never calls the network even when the keys are set. Ruff is configured in `pyproject.toml` (line-length 88) but is not a declared dependency.

## Architecture

One ticket flows through a LangGraph workflow in `support_copilot/workflow.py`: validate description → extract (LLM) → detect area → check active incident → search knowledge → confidence gate → escalate or draft (LLM). Edges stop the flow early, so a missing description, an unknown area or a known incident never reach search or drafting. Only `extract` and `draft` call the LLM; everything else is deterministic.

- `types.py`: frozen dataclasses, the `CopilotTools` and `LanguageModel` Protocols, the output contract `SupportResult` (`status`, `error_message`, `escalate`, `response`, `citations`, `confidence_score`, `owner`, `incident`, `area`, `notes`), the Pydantic LLM schemas `TicketDetails` and `DraftAnswer`, and the per-run `WorkflowState`.
- `copilot.py`: `handle_support_ticket(ticket, tools, model=None)`, the single entry point. `model` is created from the environment when omitted; tests inject a fake.
- `llm.py`: the Claude extract and draft steps, one bounded retry (timeout, 429, 5xx), and `LLMFailure` values instead of exceptions. Claude uses provider-native structured output; any other model uses tool output with no re-prompting.
- `rules.py`: pure rules. `detect_area` matches ticket text against terms taken from the ownership areas; `filter_docs` keeps only approved, internal documents; `confidence` is the share of query terms found in a document, matching an exact term or a shared five-letter prefix; `CONFIDENCE_THRESHOLD` is 0.70.
- `tools.py`: `FixtureTools` (keyword-scored search; it does **not** filter by status or access) and `build_langchain_tools`, which exposes the four fixtures as LangChain tools.
- `cli.py`: stateless CLI, one JSON object on stdout, node logs on stderr, exit 0 / 1 / 2. `demo.py` shares its JSON formatting.
- `fixture_store.py`: loads `../fixtures/*.json` and maps camelCase to snake_case. `mock_model.py` is the original deterministic starter model and is not used by the workflow.

Invariants worth knowing before changing anything: only approved, internal documents may reach the model or a citation; citations are built from the documents sent to the model, never from model text; no draft is produced on an error, incident or escalation path; a failing node becomes a safe `status="error"` result and no error text, ticket text or key is logged or printed.

## Tests and traceability

Tests are pytest with a fake chat model in `tests/conftest.py` (`FakeChatModel`, `structured_reply`, `make_fake_model`, `prompt_text`). Each test name carries its `TEST-*` and `AC-*` ids; `tests/test_traceability.py` fails when an `AC-*` in `docs/requirement/requirements.md` is not named by any test. `docs/traceability/index.md` maps requirements to design, tasks, code, tests and recorded results.

## Fixture gotchas

Fixtures contain deliberate traps: conflicting documents (KB-102 is deprecated at 72h invitation validity; KB-103 is the approved 24h version), restricted and draft documents (KB-105, KB-106), and an incident per area (INC-2041 is active for scheduling, INC-2022 is resolved). Area detection uses area-name words, so a ticket with only "patient" matches `patient-portal` and a billing ticket that also says "patient" ties with it.
