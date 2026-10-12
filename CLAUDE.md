# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Context

This is the Python starter for a Talkiatry interview exercise (60-minute timebox): build a **Product Support Copilot** that takes a Jira-style support ticket and helps a support expert decide how to handle it (answer, ask for clarification, or escalate). The task statement is in `../README.md`. The entry point to implement is `handle_support_ticket` in `support_copilot/copilot.py`, currently a placeholder that always escalates. Interview material is confidential and all data is synthetic (see `../NOTICE.md`). The sibling `../typescript/` directory is an equivalent starter; this work uses Python only.

## Commands

Run from this `python/` directory. No installs or credentials needed (stdlib only, Python 3.11+).

```bash
python3 -m unittest discover -s tests                         # all tests
python3 -m unittest tests.test_starter.StarterTests.test_mock_tools_are_available   # single test
python3 -m support_copilot.demo                               # run copilot over every fixture ticket
```

Ruff is configured in `pyproject.toml` (line-length 88) but is not a declared dependency.

## Architecture

- `support_copilot/types.py` defines all frozen dataclasses (`SupportTicket`, `KnowledgeDocument`, `SupportDecision`, `Evidence`, ...) and the two Protocols the copilot depends on: `CopilotTools` (`search_knowledge`, `find_owner`, `find_active_incidents`, plus a `model` attribute) and `LanguageModel` (`generate(system, prompt)`). The copilot should depend on these Protocols, not the concrete fixture classes. The README permits changing types/interfaces.
- `SupportDecision` is the output contract: `action` (`respond` | `clarify` | `escalate`), `message`, `evidence` (source ids plus reason), optional `owner`, and `notes`.
- `support_copilot/tools.py` provides `FixtureTools`, built by `create_fixture_tools()`. Knowledge search is simple keyword scoring (title match weighs 3, body match 1, stop words removed) and returns documents with `score` set. It does **not** filter by `status` or `access`, so deprecated/draft and restricted documents can be returned. Callers must handle that. `find_active_incidents` excludes `resolved`; owner and incident lookups match `area` case-insensitively.
- `support_copilot/mock_model.py` is a deterministic fake LLM. It echoes back the text of the first prompt line starting with `CONTEXT:` and records calls in `.calls`. It performs no reasoning, so prompts must put the content to return on a `CONTEXT:` line.
- `support_copilot/fixture_store.py` loads JSON from `../fixtures/` (repo root, i.e. `parents[2]` of the module) and maps camelCase JSON keys to snake_case dataclass fields. Data files: `tickets.json`, `knowledge.json`, `ownership.json`, `incidents.json`.
- `support_copilot/demo.py` iterates all fixture tickets through `handle_support_ticket`, creating fresh tools per ticket, and prints each decision as JSON.

## Fixture gotchas

Fixtures contain deliberate traps, such as conflicting documents (KB-102 is deprecated at 72h invitation validity; KB-103 is the approved 24h version), a `status` and `access` field on each document, and active incidents per area. Check the fixtures before assuming a search hit is trustworthy.
