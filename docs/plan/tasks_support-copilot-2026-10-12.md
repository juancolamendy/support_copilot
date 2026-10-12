# Implementation Plan: support-copilot
_Date: 2026-10-12_
_Input: docs/design/design_spec_support-copilot-2026-10-12.md_

_Plan part: 1 of 1; global phases 1–10_
_Prerequisite: none_
_Next part: none_

## Summary
Replace the placeholder `handle_support_ticket` with a LangGraph workflow (deterministic nodes plus two Claude-backed `create_agent` steps), a CLI, deterministic rules, and a pytest suite, managed with uv. Ten phases, one task each, delivered as four reviewable PRs.

## Design Waiver
- Route: SDD
- Status: N/A
- Decision: N/A — SDD used
- Requirement source: `docs/requirement/requirements.md` (AC-001 to AC-015)
- Reused pattern and boundary: N/A
- Triage checks: N/A
- Technical owner approval: N/A

## High-Risk Items (Scheduled in Phases 2–4)
- **New runtime dependencies** (langchain, langgraph, langchain-anthropic, langsmith): Phase 1 (supply-chain evidence).
- **Output contract change** (`SupportDecision` becomes `SupportResult`; breaks `copilot.py` and `demo.py`): Phase 2.
- **Document trust filter** (only approved, internal documents reach the model or citations): Phase 3.
- **Confidence cutoff reachability**: the 70% cutoff has never been tested against the fixtures, and `_terms` has no stemming ("resetting" does not match "reset"), so body-only matches score 1 against 3 for title hits. Phase 4 front-loads this and stops for a design decision if the fixture tickets cannot reach 0.70 (see Risks R1).

## Testing Strategy
- "Green" means `uv run pytest` passes offline with no network or API key, covering AC-001 to AC-008, AC-010 (scan), AC-011 to AC-015.
- Live checks (`live` marker; AC-009, AC-010 trace) run by hand with `ANTHROPIC_API_KEY` and are skipped otherwise.
- Test files reference the AC id they verify in the test name or docstring (`test_ac001_...`), which the traceability test relies on.
- Critical cases: the three fixture tickets, KB-102 never cited, restricted documents never used, escalation without a draft call, error on empty description, failure injection.
- Traceability gate: `uv run pytest tests/test_traceability.py` fails when any `AC-*` in `docs/requirement/requirements.md` is not referenced by a test under `tests/`. It does not exist yet and is created in TASK-010.

## Integration Points
- Connects to: `support_copilot/fixture_store.py` and `FixtureTools` (existing), the `CopilotTools` Protocol, Anthropic (live only), LangSmith (live only).
- Shared surfaces: `types.py` is read by every module; `demo.py` consumes the result type; `AGENTS.md` and `CLAUDE.md` list commands that change.

## Repository Evidence
- Existing patterns to reuse:
  - `support_copilot/tools.py:30` `_terms` and `:38` `_score` for tokenizing and scoring; the confidence formula reuses them.
  - `support_copilot/tools.py:47` `FixtureTools` and `:80` `create_fixture_tools`; the `@tool` wrappers delegate to these.
  - `support_copilot/types.py:76` `CopilotTools` Protocol and `:57` `LanguageModel`; the workflow depends on these, not on `FixtureTools`.
  - `support_copilot/fixture_store.py:46` `load_owners`; area terms derive from it.
  - `tests/test_starter.py`: `asyncio.run` style for async tests (new tests use pytest-asyncio).
- Git history consulted: N/A — this directory is not a git repository (see Risks R3).
- Environment: system `python3` is 3.10 while `pyproject.toml` requires >=3.11, so uv must provision the interpreter. `uv` 0.11.21 is installed.

## Data Flow and Trust Boundaries
- Input (CLI args, stdin, or fixture ticket) → validation (description present) → extraction (LLM) → area detection (deterministic) → incident check → knowledge search → filter → confidence → escalate or draft (LLM) → JSON on stdout.
- Trust boundaries: ticket text is untrusted and goes to the LLM as delimited data; LLM output is untrusted and is validated against Pydantic schemas; citations never come from the model.
- Sensitive data: API keys are read from the environment only and are never logged or printed; logs contain no ticket text. Fixtures are synthetic.

## Contract Diffs
- `SupportDecision` and `Evidence` are replaced by `SupportResult` and `Citation` (Section 4 of the SDD). Compatibility decision: breaking, internal only; the sole consumers are `copilot.py`, `demo.py` and tests, all updated in the same PRs. No external consumers. Rollback: restore the previous `types.py`, `copilot.py`, `demo.py`.
- New CLI contract (SDD 5.1) is additive.

## Migration and Rollback
- N/A — no persistent data or schema. Rollback is per phase: revert the phase's files (via git once initialised, see R3).

## Dependencies
| Dependency | Purpose | Alternatives | Provenance and review | Approval |
|---|---|---|---|---|
| langchain | `create_agent`, structured output | plain provider SDK | PyPI via uv, hashes pinned in `uv.lock`; owner to review license and advisories | Owner accepted in SDD review (2026-10-12); plan approval still required |
| langgraph | `StateGraph` workflow | plain Python pipeline | same | same |
| langchain-anthropic | Claude chat model | OpenAI, `init_chat_model` | same | same |
| langsmith | tracing | none (optional) | same | same |
| pytest, pytest-asyncio (dev) | tests | unittest + `asyncio.run` | same | same |

## Observability
- Logs: one structured stderr line per node with node name, outcome and duration; no ticket text, no secrets.
- Metrics and alerts: N/A — a local CLI has no metrics backend or alerting.
- Traces: LangSmith when `LANGSMITH_TRACING=true` and a key are set; run metadata carries ticket id and outcome.

## Threat Model and Abuse Cases
- Assets: API keys, document trust (stale or restricted content), response integrity.
- Abuse cases: prompt injection in ticket text (mitigated: delimited data, model cannot set citations, area, escalation or confidence); key leakage via output or logs (mitigated: AC-010 scan); stale-document answers (mitigated: DES-020 filter).
- Residual risk: the draft text itself can still be wrong; the human expert reviews it and later evals will measure it.

## Release and Rollback
- N/A — local prototype with no deployment, flag or rollout. Rollback is reverting the PR.

## Risks and Unresolved Decisions
| Risk / decision | Impact | Owner | Required decision or mitigation | Due before |
|---|---|---|---|---|
| R1: 0.70 cutoff may be unreachable on fixtures given no stemming and weight 1 for body matches | AC-001/AC-002 would escalate instead of answering | project owner | TASK-004 measures it. If TCK-1001 or TCK-1002 score below 0.70, stop and amend the SDD (e.g. term-coverage formula or a different cutoff); do not tune silently | Phase 5 | **MEASURED 2026-10-12 (read-only, before any Phase 4 code):** with the SDD formula `_score / (3 x terms)` the correct top document scores 0.57 for TCK-1001 (KB-101, query = title terms + `password, reset, email, link`) and 0.50 for TCK-1002 (KB-103, query = title terms + `invitation, expired, portal, link`), both below 0.70, so AC-001 and AC-002 would escalate. Retrieval ranking itself is correct (right document is top). **RESOLVED 2026-10-12:** the owner chose term coverage with the 0.70 cutoff kept; SDD draft 2 amends DES-027 and Section 9.
| R2: a fake chat model may not drive `create_agent` structured output | Phase 6 and 7 tests need another seam | project owner | Preferred: custom fake chat model with `bind_tools`. Fallback: inject at an `Extractor`/`Drafter` seam in `llm.py` and note it in the SDD | Phase 6 |
| R3: no git repository, so there are no atomic commits or revert boundaries | Plan's commit and rollback steps cannot run | project owner | RESOLVED: `python/` turned out to have an existing git history; baseline commit 432b52c made and work is on branch `plan/support-copilot` (no separate worktree) | Phase 1 |
| R4: Python 3.10 on PATH vs `requires-python >=3.11` | `python3 -m pytest` fails outside uv | project owner | Always run via `uv run`; uv provisions 3.11+ | Phase 1 |

## Assumptions
- None beyond the SDD, apart from the named risks above.

## Human Quality Gates

### Plan Approval
- Status: Approved
- Required reviewers: technical owner
- Artifact revision: draft 1 (2026-10-12)
- Decision and conditions: Owner ran `/cg-exec 1` after the plan summary asked them to confirm or change it, and chose "git init + baseline commit" for R3. R1, R2 and R4 remain open and are handled in their phases.
- Evidence: conversation record, 2026-10-12
- Approved by / at: project owner, 2026-10-12

Any material plan edit resets this approval to `Pending`. `cg-exec` must not start Phase 1 until this gate is approved for the current revision.

### Checkpoint Approvals
| Checkpoint | Prerequisite phases | Status | Artifact revision | Evidence / approver |
|---|---|---|---|---|
| Checkpoint 1 | Phases 1–3 | Approved | plan revision after Phase 3 (2026-10-12) | Covers RESULT-001 to RESULT-009 (Phases 1–3 green, 26 tests). Project owner replied "continue" on 2026-10-12 |
| Checkpoint 2 | Phases 4–6 | Pending | n/a | n/a |
| Final | Phases 7–10 | Pending | n/a | n/a |

## Layer Coverage
| Layer | In scope? | Phase(s) |
|-------|-----------|----------|
| Schema / migrations | N/A (no database) | — |
| Backend / API / services | Y | 2, 3, 4, 5, 6, 7, 8, 9 |
| Frontend | N/A (CLI only, UI out of scope) | — |
| Tests (fixtures / e2e) | Y | 1, 6, 10 (plus per-phase TDD) |
| Docs / AGENTS.md | Y | 10 |
| Config / deps | Y | 1 |

## Pull Request LOC Validation
| Proposed PR | Phases | Reviewable authored LOC (upper bound) | Exception LOC | Status / required action |
|-------------|--------|---------------------------------------|---------------|--------------------------|
| PR 1 | 1–4 | 435 | `uv.lock` churn reported separately | WARNING: large PR |
| PR 2 | 5–6 | 400 | none | Target |
| PR 3 | 7–8 | 575 | none | WARNING: large PR |
| PR 4 | 9–10 | 350 | none | Target |

- Split or justification: not required (every PR is at or under 800). PR 1 stays together because the contract, rules and confidence calibration (R1) should be reviewed as one foundation; PR 3 stays together because both phases edit one graph.
- Enhanced review strategy: not required.

## Task Dependency Graph
| Task | Depends on | Inputs supplied by dependencies | Topological order | Delegation / parallelization |
|------|------------|---------------------------------|-------------------|------------------------------|
| TASK-001 | None | — | 1 | Sequential |
| TASK-002 | TASK-001 | pytest, pydantic available | 2 | Sequential |
| TASK-003 | TASK-001 | pytest | 3 | Safe to parallelize with 005 and 006 |
| TASK-004 | TASK-003 | `rules.py` module | 4 | Sequential |
| TASK-005 | TASK-001 | langchain-core tools | 5 | Safe to parallelize with 003 and 006 |
| TASK-006 | TASK-001, TASK-002 | `TicketDetails`, `DraftAnswer` | 6 | Safe to parallelize with 003 and 005 |
| TASK-007 | TASK-002, TASK-003, TASK-005, TASK-006 | result type, rules, tool wrappers, extract agent and fakes | 7 | Sequential |
| TASK-008 | TASK-004, TASK-007 | confidence, workflow graph | 8 | Sequential |
| TASK-009 | TASK-008 | working `handle_support_ticket` | 9 | Sequential |
| TASK-010 | TASK-009 | CLI and all tests | 10 | Sequential |

## Git isolation
This directory is not a git repository (R3), so no worktree is created. If you initialise git first: `git worktree add .worktree/support-copilot -b plan/support-copilot`. No extra worktrees.

## Phases

### Phase 1 — Tooling and dependencies
**Goal:** `uv run pytest` works offline from a clean checkout with the approved dependencies.
**Size:** S
**Files affected:** `pyproject.toml`, `uv.lock` (generated), `tests/test_tooling.py`
**Task:**
- [x] TASK-001 — uv project with dependencies, pytest config and `live` marker

  **Requirements:** REQ-F-010 (constraint; no AC)
  **Design:** DES-018, DES-024
  **Changes:** CHG-001
  **Tests:** TEST-001
  **Depends on:** None

  **Outcome:** `uv sync` installs the runtime and dev dependencies and `uv run pytest` collects and passes the existing `tests/test_starter.py`.

  **Inputs:** current `pyproject.toml` (requires-python >=3.11, ruff config), SDD sections 5.4, 7.
  **Constraints:** only the approved dependencies; no secrets; network is needed only for the install.
  **Rollback:** restore the original `pyproject.toml` and delete `uv.lock`.
  **Measurement:** exit codes of `uv sync` and `uv run pytest`.

  **Allowed changes:**
  - `pyproject.toml`
  - `uv.lock`
  - `tests/test_tooling.py`

  **Do not change:** `[tool.ruff]` settings, the `requires-python` constraint, `tests/test_starter.py`.

  **Implementation steps:**
  1. Write `tests/test_tooling.py` first (red: imports fail).
  2. Add dependencies, dev group, `asyncio_mode = "auto"` and the `live` marker.
  3. Run the required checks.

  **Expected artifacts:** `pyproject.toml`, `uv.lock`, `tests/test_tooling.py`
  **Expected LOC impact:** production +0; tests +10–15; docs/config +15–25; confidence: high; basis: `pyproject.toml` is 8 lines today. `uv.lock` churn excluded.
  **Required checks:** `uv sync`; `uv run pytest`
  **Policy evidence:** new runtime dependency → justification and alternatives in "Dependencies" above; license/advisory review by the owner recorded in the completion evidence; SBOM N/A (prototype, nothing released).
  **Objective-evidence mapping:** REQ-F-010 (no AC) → imports succeed → TEST-001 → pytest result → RESULT allocated by `cg-exec`.
  **Test derivation:**

  | TEST ID | AC ID | Test level | Level role | Precondition / controlled data | Trigger | Positive oracle | Negative oracle | Boundary or failure |
  |---|---|---|---|---|---|---|---|---|
  | TEST-001 | N/A (REQ-F-010) | unit | Primary | clean uv environment | import `create_agent`, `StateGraph`, `ChatAnthropic`, `langsmith` | imports succeed | missing dependency fails the test | marker `live` registered (no warnings) |

  **Completion evidence (2026-10-12):**
  - Changed files: `pyproject.toml`, `uv.lock`, `tests/test_tooling.py`, this plan, `docs/traceability/index.md`.
  - RESULT-001 (red baseline): `uv run --no-project --python 3.12 --with pytest pytest tests/test_tooling.py -q` — exit 1; 2 selected, 0 passed, 2 failed (`ModuleNotFoundError` on the imports; `live` marker not registered).
  - RESULT-002 (focused green): `uv run pytest tests/test_tooling.py -q` — exit 0; 2 selected, 2 passed, 0 failed, 0 skipped. `uv sync` — exit 0.
  - RESULT-003 (full suite): `uv run pytest -q` — exit 0; 4 selected, 4 passed, 0 failed, 0 skipped (2 starter + 2 TEST-001). `uv run python -m support_copilot.demo` — runs, placeholder output unchanged.
  - Resolved versions in `uv.lock`: langchain >=1.4.5, langchain-anthropic >=1.7.6, langgraph >=1.2.14, langsmith >=0.14.7, pytest 9.1.1, pytest-asyncio 1.4.0. uv provisioned Python 3.12.8 (system python3 is 3.10), which resolves R4 when commands run through `uv run`.
  - Discovered decisions: (1) `pythonpath = ["."]` added to the pytest config because `tests/` is not a package and `support_copilot` was otherwise not importable; (2) `[tool.uv] package = false` set explicitly (the project has no build backend); (3) `addopts = "--strict-markers"` so a misspelled marker fails instead of being ignored. Follow-up: none discovered.
  - Remaining uncertainty: the license and security-advisory review required by the policy evidence has NOT been performed by this run; the owner must review `uv.lock` before merge. The traceability gate (TASK-010) does not exist yet.

**Expected authored LOC:** tests +10–15; config +15–25
**Success criteria:** `uv run pytest` exits 0 with the starter tests plus TEST-001; `uv.lock` committed.
**Commit message:** `chore: add uv dependencies and pytest configuration`
**Git:** plan worktree (see Git isolation).

### Phase 2 — Output contract and types
**Goal:** `SupportResult`, `Citation`, `TicketDetails`, `DraftAnswer` and the workflow state exist, and the repo still runs.
**Size:** S
**Files affected:** `support_copilot/types.py`, `support_copilot/copilot.py`, `tests/test_types.py`
**Task:**
- [x] TASK-002 — Replace `SupportDecision` with `SupportResult` and add LLM schemas

  **Requirements:** REQ-F-008, REQ-F-002; AC-013 (secondary)
  **Design:** DES-012, DES-013, DES-014
  **Changes:** CHG-002, CHG-003
  **Tests:** TEST-002
  **Depends on:** TASK-001

  **Outcome:** the result and schema types match SDD Section 4, and `handle_support_ticket` returns a valid error `SupportResult` placeholder.

  **Inputs:** SDD Section 4; `types.py:61-74` (`Evidence`, `SupportDecision`).
  **Constraints:** frozen dataclasses for results; Pydantic only for LLM schemas; `Citation` replaces `Evidence`.
  **Rollback:** restore `types.py` and `copilot.py`.
  **Measurement:** `tests/test_types.py` pass count.

  **Allowed changes:**
  - `support_copilot/types.py`
  - `support_copilot/copilot.py`
  - `tests/test_types.py`

  **Do not change:** `SupportTicket`, `KnowledgeDocument`, `ServiceOwner`, `Incident`, the `CopilotTools` and `LanguageModel` Protocols, `demo.py`.

  **Implementation steps:**
  1. Write `TEST-002` (red: types missing).
  2. Implement the types and update the placeholder in `copilot.py`.
  3. Run the required checks, including the demo.

  **Expected artifacts:** the three files above
  **Expected LOC impact:** production +40–60 / ~15 modified; tests +30–45; docs/config +0; confidence: high; basis: `types.py` dataclass style at `:61-74`.
  **Required checks:** `uv run pytest tests/test_types.py`; `uv run pytest`; `uv run python -m support_copilot.demo`
  **Policy evidence:** public contract change → contract diff in "Contract Diffs", internal-only compatibility decision, rollback above.
  **Objective-evidence mapping:** AC-013 (secondary: field set and defaults) → domain service → TEST-002 → pytest result. The primary AC-013 check is TEST-016.
  **Test derivation:**

  | TEST ID | AC ID | Test level | Level role | Precondition / controlled data | Trigger | Positive oracle | Negative oracle | Boundary or failure |
  |---|---|---|---|---|---|---|---|---|
  | TEST-002 | AC-013 | unit | Secondary — proves the contract shape before any outcome exists | none | construct `SupportResult` with defaults | fields equal the SDD list; `escalate` False; `citations` empty | mutation of a frozen instance raises | `TicketDetails` rejects a missing `summary` |

  **Completion evidence (2026-10-12):**
  - Changed files: `support_copilot/types.py`, `support_copilot/copilot.py`, `tests/test_types.py`, this plan, `docs/traceability/index.md`.
  - RESULT-004 (red baseline): `uv run pytest tests/test_types.py -q` — exit 2; collection error `ImportError: cannot import name 'Citation'`; 0 selected.
  - RESULT-005 (focused green): `uv run pytest tests/test_types.py -q` — exit 0; 9 selected, 9 passed, 0 failed, 0 skipped.
  - RESULT-006 (full suite): `uv run pytest -q` — exit 0; 13 selected, 13 passed, 0 failed, 0 skipped (2 starter + 2 TEST-001 + 9 TEST-002). `uv run python -m support_copilot.demo` — exit 0; each ticket prints the `SupportResult` error placeholder with all contract fields.
  - Discovered decisions: (1) `SupportResult` gets a `ResultStatus` literal (`"ok" | "error"`) and `SupportAction` is removed, per SDD Section 4; (2) `TicketDetails.symptoms` and `product_terms` default to empty lists so a model that omits them does not fail validation, while `summary` stays required; (3) `WorkflowState` is a `total=False` TypedDict so each node can return a partial update.
  - Follow-ups: (a) `pydantic` is imported directly but is only a transitive dependency of `langchain`; the owner should decide whether to declare it in `pyproject.toml` (a change outside this task's allowed files); (b) `CLAUDE.md` still describes `SupportDecision`/`Evidence` and is updated in TASK-010; (c) `types.py:119` (existing `find_active_incidents` Protocol line) is 89 characters, over the ruff limit of 88; left untouched as pre-existing.
  - Remaining uncertainty: the primary AC-013 check (all five outcomes) lands in TASK-008 (TEST-016); this phase proves only the shape and defaults.

**Expected authored LOC:** production +40–75; tests +30–45
**Success criteria:** `uv run pytest` and the demo both run without import errors.
**Commit message:** `feat: add SupportResult output contract and LLM schemas`
**Git:** plan worktree.

### Phase 3 — Area detection and document filter
**Goal:** deterministic area detection and the approved-and-internal filter.
**Size:** S
**Files affected:** `support_copilot/rules.py`, `tests/test_rules.py`
**Task:**
- [x] TASK-003 — `detect_area` and `filter_docs`

  **Requirements:** REQ-F-003a, REQ-F-005; AC-005, AC-008
  **Design:** DES-004, DES-008, DES-020, DES-026, DES-028
  **Changes:** CHG-004
  **Tests:** TEST-003, TEST-004
  **Depends on:** TASK-001

  **Outcome:** `detect_area(title, description, owners)` returns an area or `None`; `filter_docs(docs)` keeps only `status == "approved"` and `access == "internal"`.

  **Inputs:** `load_owners` (`fixture_store.py:46`), `_terms` (`tools.py:30`), fixtures `ownership.json`, `knowledge.json`.
  **Constraints:** no LLM, no I/O inside the functions (owners and documents are passed in); a term shared by more than one area is ignored; ties go to `ownership.json` order.
  **Rollback:** delete the new files.
  **Measurement:** TEST-003 and TEST-004 results.

  **Allowed changes:**
  - `support_copilot/rules.py`
  - `tests/test_rules.py`

  **Do not change:** `tools.py` scoring, fixture files.

  **Implementation steps:**
  1. Write TEST-003 and TEST-004 (red: module missing).
  2. Implement `detect_area` and `filter_docs`.
  3. Run the required checks.

  **Expected artifacts:** `support_copilot/rules.py`, `tests/test_rules.py`
  **Expected LOC impact:** production +45–70; tests +60–90; confidence: medium; basis: `_terms` at `tools.py:30` and the SDD Section 9 algorithm.
  **Required checks:** `uv run pytest tests/test_rules.py`; `uv run pytest`
  **Policy evidence:** N/A — no contract, dependency or permission change beyond Phase 1.
  **Objective-evidence mapping:** AC-005 → domain service → TEST-003 → pytest result; AC-008 → domain service → TEST-004 → pytest result.
  **Test derivation:**

  | TEST ID | AC ID | Test level | Level role | Precondition / controlled data | Trigger | Positive oracle | Negative oracle | Boundary or failure |
  |---|---|---|---|---|---|---|---|---|
  | TEST-003 | AC-005 | unit | Primary | `ownership.json` owners; the three fixture tickets | `detect_area` | TCK-1001 and TCK-1002 give `patient-portal`, TCK-1003 gives `scheduling` | text with no area terms returns `None` | a term shared by two areas is ignored |
  | TEST-004 | AC-008 | unit | Primary | `knowledge.json` (KB-101 to KB-106) | `filter_docs` | result ids are exactly KB-101, KB-103, KB-104 | KB-102 (deprecated), KB-105 (restricted), KB-106 (draft, restricted) absent | empty input returns empty |

  **Completion evidence (2026-10-12):**
  - Changed files: `support_copilot/rules.py` (new), `tests/test_rules.py` (new), this plan, `docs/traceability/index.md`.
  - RESULT-007 (red baseline): `uv run pytest tests/test_rules.py -q` — exit 2; collection error `ModuleNotFoundError: No module named 'support_copilot.rules'`; 0 selected.
  - RESULT-008 (focused green): `uv run pytest tests/test_rules.py -q` — exit 0; 13 selected, 13 passed, 0 failed, 0 skipped (TEST-003: 9 cases incl. 3 parametrized; TEST-004: 4 cases).
  - RESULT-009 (full suite): `uv run pytest -q` — exit 0; 26 selected, 26 passed, 0 failed, 0 skipped.
  - Discovered decisions: (1) the SDD's "prefer the longest matched term" mitigation is implemented as a tie-break after the matched-term count and before ownership order, and is covered by a test; (2) `_terms` is imported from `tools.py` as the plan directed, which means `rules.py` depends on a private name; (3) an area name made only of stop words or one-letter tokens has no terms and can never match.
  - Follow-ups: make `_terms` public (rename in `tools.py`, a file outside this task) so `rules.py` does not import a private name; the same applies to TASK-004, which reuses `_score`.
  - Remaining uncertainty: synonym coverage. Detection leans on area-name words, so a ticket that says only "invitation" or "slots" without "portal", "scheduling" or "billing" yields no area (a clarification error by design, DES-026). A ticket mentioning only "patient" (e.g. "patient cannot book") matches `patient-portal` because `patient` is unique to that area in the current `ownership.json`.

**Expected authored LOC:** production +45–70; tests +60–90
**Success criteria:** `rules.py` passes TEST-003 and TEST-004 with no network or LLM use.
**Commit message:** `feat: add deterministic area detection and document filter`
**Git:** plan worktree.

### Phase 4 — Confidence score and calibration
**R1 RESOLVED (2026-10-12).** The SDD weighted formula could not reach 0.70 on the answerable fixtures (0.57 and 0.50). The owner chose term coverage with the 0.70 cutoff kept; SDD draft 2 amends DES-027 and Section 9 accordingly. Measured with coverage (share of query terms found in the document title or body, using the existing `_score` > 0 test): TCK-1001 top KB-101 = 0.86; TCK-1002 top KB-103 = 1.00; TCK-1003 top KB-104 = 0.43; a billing-like and an unrelated query = 0.00 for every approved document.
**Goal:** a deterministic confidence score, with a measured check that the 0.70 cutoff is reachable on the fixtures.
**Size:** S
**Files affected:** `support_copilot/rules.py`, `tests/test_confidence.py`
**Task:**
- [x] TASK-004 — `confidence` and fixture calibration

  **Requirements:** REQ-F-006a; AC-007 (and AC-001 secondary)
  **Design:** DES-008, DES-027
  **Changes:** CHG-005
  **Tests:** TEST-005, TEST-006
  **Depends on:** TASK-003

  **Outcome:** `confidence(query_terms, document)` returns the share of query terms found in the document (0–1) and `CONFIDENCE_THRESHOLD = 0.70` exists; the fixture tickets' scores are recorded.

  **Inputs:** `_score` (`tools.py:38`); SDD Section 9 term-coverage formula (draft 2); canned `product_terms` for TCK-1001 and TCK-1002; query terms are the ticket title terms plus `product_terms`.
  **Constraints:** deterministic; 0–1 by construction; the cutoff and formula are fixed by SDD draft 2 ("Ask first" to change).
  **Rollback:** remove `confidence` and its tests.
  **Measurement:** computed scores for TCK-1001 and TCK-1002 against their expected documents, written into the completion evidence.

  **Allowed changes:**
  - `support_copilot/rules.py`
  - `tests/test_confidence.py`

  **Do not change:** the 0.70 cutoff, `tools.py` scoring, the SDD.

  **Implementation steps:**
  1. Write TEST-005 and TEST-006 (red).
  2. Implement `confidence`.
  3. Run the checks. If TEST-006 fails, **stop**: do not tune the formula or cutoff; report to the owner.

  **Expected artifacts:** `support_copilot/rules.py`, `tests/test_confidence.py`
  **Expected LOC impact:** production +20–30; tests +50–80; confidence: medium; basis: SDD Section 9 formula; test size depends on canned terms.
  **Required checks:** `uv run pytest tests/test_confidence.py`; `uv run pytest`
  **Policy evidence:** a material behavior risk accepted only by the owner → R1 decision recorded (owner chose term coverage, 2026-10-12).
  **Objective-evidence mapping:** AC-007 → domain service → TEST-005 → pytest result; AC-001 (secondary) → TEST-006 → recorded scores.
  **Test derivation:**

  | TEST ID | AC ID | Test level | Level role | Precondition / controlled data | Trigger | Positive oracle | Negative oracle | Boundary or failure |
  |---|---|---|---|---|---|---|---|---|
  | TEST-005 | AC-007 | unit | Primary | fixed documents and term sets | `confidence` twice per input | identical scores on repeat; every term present gives 1.0; half the terms present gives 0.5; a body-only term counts | no overlap gives 0.0; score always within 0 to 1 | empty term set returns 0.0 without error; `CONFIDENCE_THRESHOLD == 0.70` |
  | TEST-006 | AC-001 | unit | Secondary — proves the cutoff is reachable on real fixtures, a risk the primary integration test would hide behind a fake | KB-101 and KB-103 with canned `product_terms` | `confidence` for TCK-1001 and TCK-1002 | top approved document is KB-101 and KB-103, and both scores >= 0.70 | an unrelated query scores 0.0 for every approved document | a failure here reopens R1 |

  **Completion evidence (2026-10-12):**
  - Changed files: `support_copilot/rules.py`, `tests/test_confidence.py` (new), this plan, the SDD (separate commit `7e2d63e`), `docs/traceability/index.md`.
  - RESULT-010 (red baseline): `uv run pytest tests/test_confidence.py -q` — exit 2; collection error `ImportError: cannot import name 'CONFIDENCE_THRESHOLD'`; 0 selected.
  - RESULT-011 (focused green): `uv run pytest tests/test_confidence.py -q` — exit 0; 10 selected, 10 passed, 0 failed, 0 skipped (TEST-005: 7; TEST-006: 3 incl. 2 parametrized).
  - RESULT-012 (full suite): `uv run pytest -q` — exit 0; 36 selected, 36 passed, 0 failed, 0 skipped.
  - Measured scores (search over approved, internal documents; query = title terms + canned `product_terms`): TCK-1001 → KB-101 search score 12, confidence 0.857; next hits KB-103 0.714, KB-104 0.143. TCK-1002 → KB-103 search score 6, confidence 1.000; next hits KB-101 0.750, KB-104 0.250. Both expected documents are top and clear 0.70.
  - R1 outcome: the original weighted formula measured 0.57 and 0.50 before any code; the owner chose term coverage with the 0.70 cutoff kept (asked twice, same answer); SDD draft 2 amends DES-027 and Section 9 (commit `7e2d63e`).
  - Discovered decisions: (1) `CONFIDENCE_THRESHOLD = 0.70` is defined in `rules.py` for Phase 8 to import; (2) `_score(term, doc) > 0` is reused as the "term found" test, so `confidence` shares the tokenizer and its lack of stemming; (3) the tests canned the `product_terms` a model would return, so the real extraction step may produce different terms.
  - Follow-ups: none new beyond the earlier `_terms`/`_score` public-rename follow-up.
  - Remaining uncertainty: coverage does not tell similar documents apart — KB-103 also scores 0.714 on the TCK-1001 query and would pass the cutoff, so a correct citation relies on the search ranking choosing the top document. With real model-extracted terms the scores may differ; the live checks in TASK-010 will show this.

**Expected authored LOC:** production +20–30; tests +50–80
**Success criteria:** TEST-005 and TEST-006 pass, or the phase stops with R1 raised.
**Commit message:** `feat: add term-coverage confidence score`
**Git:** plan worktree.

### Checkpoint: After Phases 1–3
- [ ] All tests pass
- [ ] `uv sync` and `uv run pytest` work from a clean state
- [ ] Contract and rules in place
- [ ] Review with human before proceeding
- [ ] Record an Approved checkpoint gate before Phase 4

### Phase 5 — Fixture tool wrappers
**Goal:** the four fixtures are callable as LangChain tools.
**Size:** S
**Files affected:** `support_copilot/tools.py`, `tests/test_tool_wrappers.py`
**Task:**
- [x] TASK-005 — `@tool` wrappers for tickets, incidents, knowledge, ownership

  **Requirements:** REQ-F-009; AC-014
  **Design:** DES-007
  **Changes:** CHG-006
  **Tests:** TEST-007
  **Depends on:** TASK-001

  **Outcome:** `build_langchain_tools(tools)` returns four tools that delegate to `CopilotTools` and `load_tickets`.

  **Inputs:** `FixtureTools` (`tools.py:47`), `load_tickets` (`fixture_store.py:17`), fixtures.
  **Constraints:** wrappers delegate; no new logic; the existing `FixtureTools` behavior is unchanged.
  **Rollback:** remove the wrapper function and its test.
  **Measurement:** TEST-007 result.

  **Allowed changes:**
  - `support_copilot/tools.py`
  - `tests/test_tool_wrappers.py`

  **Do not change:** `search_knowledge` scoring, `_terms`, `_score`.

  **Implementation steps:**
  1. Write TEST-007 (red).
  2. Add the wrappers.
  3. Run the checks.

  **Expected artifacts:** the two files above
  **Expected LOC impact:** production +40–60; tests +40–60; confidence: medium; basis: `tools.py:47-80` method signatures to mirror.
  **Required checks:** `uv run pytest tests/test_tool_wrappers.py`; `uv run pytest`
  **Policy evidence:** N/A — no contract change beyond the in-process tool interface already in the SDD.
  **Objective-evidence mapping:** AC-014 → domain service → TEST-007 → pytest result.
  **Test derivation:**

  | TEST ID | AC ID | Test level | Level role | Precondition / controlled data | Trigger | Positive oracle | Negative oracle | Boundary or failure |
  |---|---|---|---|---|---|---|---|---|
  | TEST-007 | AC-014 | contract | Primary | the four fixture files | invoke each tool | incidents for `scheduling` include INC-2041; an invitation query includes KB-103; owner for `patient-portal` is "Portal Platform"; `get_ticket("TCK-1001")` returns that ticket | unknown ticket id returns a clear error value, not an exception | resolved incident INC-2022 not returned |

  **Completion evidence (2026-10-12):**
  - Changed files: `support_copilot/tools.py` (added `build_langchain_tools`; `FixtureTools`, `_terms`, `_score` unchanged), `tests/test_tool_wrappers.py` (new), this plan, `docs/traceability/index.md`.
  - RESULT-013 (red baseline): `uv run pytest tests/test_tool_wrappers.py -q` — exit 2; collection error `ImportError: cannot import name 'build_langchain_tools'`; 0 selected.
  - RESULT-014 (focused green): `uv run pytest tests/test_tool_wrappers.py -q` — exit 0; 9 selected, 9 passed, 0 failed, 0 skipped.
  - RESULT-015 (full suite): `uv run pytest -q` — exit 0; 45 selected, 45 passed, 0 failed, 0 skipped.
  - Source-driven check: langchain 1.4.5 / langchain-core 1.6.10. The docs page fetched shows `@tool` and `tool.invoke`; the async `StructuredTool.from_function(coroutine=...)` form was not shown there and is verified by the tests against the installed version.
  - Discovered decisions: (1) tools return JSON-friendly `dict`/`list[dict]` via `dataclasses.asdict` instead of dataclasses, so a tool result can be serialized into a model message; (2) a miss returns `{"error": ...}` rather than raising or returning `None`, for `get_ticket` and `find_owner`; (3) the ticket tool reads `load_tickets()` directly because tickets are not part of the `CopilotTools` Protocol.
  - Follow-ups: (a) **security note** — the wrappers mirror `FixtureTools`, so `search_knowledge` returns deprecated, draft and restricted documents unfiltered; the DES-020 filter (`rules.filter_docs`) must be applied by the caller, and the `search_knowledge` tool must not be bound directly to an LLM without it. The design calls the tools from graph nodes, which filter, so nothing is exposed today. (b) `tools.py` now imports `langchain_core`, so `rules.py` (which imports `tools.py`) does too.
  - Remaining uncertainty: none for this phase; tool schemas for a model-driven agent were not exercised because the design never lets the model choose tools.

**Expected authored LOC:** production +40–60; tests +40–60
**Success criteria:** TEST-007 passes and existing tests still pass.
**Commit message:** `feat: expose fixtures as LangChain tools`
**Git:** plan worktree; safe to run concurrently with Phases 3 and 6 if a checkout exists.

### Phase 6 — LLM adapter and test doubles
**Goal:** extraction and drafting agents with timeout, one retry, and a fake model for tests.
**Size:** M
**Files affected:** `support_copilot/llm.py`, `tests/conftest.py`, `tests/test_llm.py`
**Task:**
- [ ] TASK-006 — `llm.py` with `create_agent` extract and draft steps

  **Requirements:** REQ-F-002, REQ-F-007, REQ-NF-002; AC-012, AC-015 (secondary)
  **Design:** DES-006, DES-015, DES-017, DES-019, DES-024
  **Changes:** CHG-007, CHG-008
  **Tests:** TEST-008, TEST-009
  **Depends on:** TASK-001, TASK-002

  **Outcome:** `extract_details(model, ticket)` and `draft_answer(model, details, documents)` return validated schemas or an error value; `conftest.py` provides a fake chat model and call recorder.

  **Inputs:** `TicketDetails` and `DraftAnswer` from TASK-002; env vars `COPILOT_MODEL`, `ANTHROPIC_API_KEY`.
  **Constraints:** 4 s timeout; one retry with backoff on timeout, 429, 5xx; validation failures are not retried; the API key is never logged; prompts keep ticket text in delimited sections; at most 3 documents in the draft prompt (DES-022).
  **Rollback:** delete the new files.
  **Measurement:** TEST-008 and TEST-009 results; the fake model's call count.

  **Allowed changes:**
  - `support_copilot/llm.py`
  - `tests/conftest.py`
  - `tests/test_llm.py`

  **Do not change:** `types.py` schemas, `mock_model.py`.

  **Implementation steps:**
  1. Write TEST-008, TEST-009 and the fake model (red).
  2. Implement `llm.py`. If the fake cannot drive `create_agent` (R2), stop and raise it.
  3. Run the checks.

  **Expected artifacts:** the three files above
  **Expected LOC impact:** production +70–110; tests +110–170 (conftest +50–80, test_llm +60–90); confidence: low; basis: R2, fake-model support for `create_agent` is unverified.
  **Required checks:** `uv run pytest tests/test_llm.py`; `uv run pytest`
  **Policy evidence:** credential handling → keys from the environment only (verified later by TEST-020); new external service → Anthropic approved in the SDD review.
  **Objective-evidence mapping:** AC-012 → domain service → TEST-008 → pytest result; AC-015 (secondary) → TEST-009 → pytest result.
  **Test derivation:**

  | TEST ID | AC ID | Test level | Level role | Precondition / controlled data | Trigger | Positive oracle | Negative oracle | Boundary or failure |
  |---|---|---|---|---|---|---|---|---|
  | TEST-008 | AC-012 | unit | Primary | fake model returning canned `TicketDetails` JSON | `extract_details` | valid `TicketDetails` with summary, symptoms, product_terms | malformed canned output returns an error value, no exception | empty description never reaches the model (guard by caller) |
  | TEST-009 | AC-015 | resilience | Secondary — proves the retry and timeout policy at the adapter, which the workflow-level test cannot isolate | fake model raising timeout once, then succeeding; and twice | `extract_details` | one retry then success; call count is 2 | two failures return an error value, call count is 2 (no third) | 4xx-style validation error is not retried (call count 1) |

  **Completion evidence:** changed files; red/green commands and exit codes; R2 outcome; discovered decisions; remaining uncertainty

**Expected authored LOC:** production +70–110; tests +110–170
**Success criteria:** TEST-008 and TEST-009 pass offline; the fake model and recorder are importable by later phases.
**Commit message:** `feat: add Claude extract and draft steps with test doubles`
**Git:** plan worktree; safe to run concurrently with Phases 3 and 5.

### Checkpoint: After Phases 4–6
- [ ] All tests pass
- [ ] R1 (confidence reachability) and R2 (fake model) resolved or decided
- [ ] High-risk items addressed: filter, contract, dependencies, confidence
- [ ] Review with human before proceeding
- [ ] Record an Approved checkpoint gate before the next phase

### Phase 7 — Workflow: validation, extraction, area, incident stop
**Goal:** the graph's front half and early stops work end to end, wired into `handle_support_ticket`.
**Size:** M
**Files affected:** `support_copilot/workflow.py`, `support_copilot/copilot.py`, `tests/test_workflow_stops.py`
**Task:**
- [ ] TASK-007 — Graph nodes validate, extract, detect_area, check_incident, with error and incident stops

  **Requirements:** REQ-F-003, REQ-F-003a, REQ-F-004, REQ-NF-004; AC-003, AC-004, AC-005 (secondary)
  **Design:** DES-002, DES-003, DES-004, DES-009, DES-010, DES-016, DES-023, DES-030, DES-031
  **Changes:** CHG-009, CHG-010
  **Tests:** TEST-010, TEST-011, TEST-012
  **Depends on:** TASK-002, TASK-003, TASK-005, TASK-006

  **Outcome:** `handle_support_ticket(ticket, tools, model=None)` returns the error result for a missing description or area, and the incident result for TCK-1003, without a drafting call or a knowledge search.

  **Inputs:** `SupportResult`, `rules.detect_area`, extract step and fake model, `find_active_incidents`, `find_owner`.
  **Constraints:** validation runs before extraction; routing lives in graph edges; no ticket text in logs; no draft call on these paths.
  **Rollback:** restore `copilot.py` placeholder; delete `workflow.py`.
  **Measurement:** call recorder counts (extract, search, draft) and the three test results.

  **Allowed changes:**
  - `support_copilot/workflow.py`
  - `support_copilot/copilot.py`
  - `tests/test_workflow_stops.py`

  **Do not change:** `rules.py` behavior, `types.py` fields.

  **Implementation steps:**
  1. Write TEST-010 to TEST-012 (red).
  2. Implement the nodes, edges and node logging; wire `copilot.py`.
  3. Run the checks.

  **Expected artifacts:** the three files above
  **Expected LOC impact:** production +90–130 / ~15 modified; tests +90–130; confidence: medium; basis: LangGraph conditional-edge pattern from the docs and SDD 3.1.
  **Required checks:** `uv run pytest tests/test_workflow_stops.py`; `uv run pytest`
  **Policy evidence:** observability → stderr logging without ticket text (SDD 6, DES-023); `N/A` for other triggers.
  **Objective-evidence mapping:** AC-003 → domain service → TEST-010 → pytest result with zero search/draft calls; AC-004 → TEST-011; AC-005 (secondary) → TEST-012.
  **Test derivation:**

  | TEST ID | AC ID | Test level | Level role | Precondition / controlled data | Trigger | Positive oracle | Negative oracle | Boundary or failure |
  |---|---|---|---|---|---|---|---|---|
  | TEST-010 | AC-003 | integration | Primary | TCK-1003, `FixtureTools`, fake model, call recorder | `handle_support_ticket` | ok, `escalate` false, `response` None, incident INC-2041, owner "Care Access Engineering" and "#help-care-access" | search and draft call counts are 0 | resolved incidents ignored |
  | TEST-011 | AC-004 | unit | Primary | ticket with empty description | `handle_support_ticket` | `status == "error"`, message contains `description`, `escalate` false | extract call count is 0, `response` None | whitespace-only description also rejected |
  | TEST-012 | AC-005 | integration | Secondary — proves the routing edge from area failure to the error stop, which the pure function test cannot | description with no area terms, fake extract output | `handle_support_ticket` | `status == "error"`, message contains `area` | incident and search call counts are 0 | unknown area never reaches `find_owner` |

  **Completion evidence:** changed files; red/green commands and exit codes; call counts; discovered decisions; remaining uncertainty

**Expected authored LOC:** production +105–145; tests +90–130
**Success criteria:** TEST-010 to TEST-012 pass and the demo runs for TCK-1003 without a model call beyond extraction.
**Commit message:** `feat: add workflow validation, area detection and incident stop`
**Git:** plan worktree.

### Phase 8 — Workflow: search, escalate, draft, failures
**Goal:** the full flow including filtering, confidence gating, escalation, drafting, citations and failure handling.
**Size:** M
**Files affected:** `support_copilot/workflow.py`, `tests/test_workflow_answer.py`, `tests/test_workflow_failure.py`
**Task:**
- [ ] TASK-008 — Knowledge search, filter, confidence gate, escalate and draft nodes

  **Requirements:** REQ-F-005, REQ-F-006, REQ-F-006a, REQ-F-007, REQ-F-008, REQ-NF-002; AC-001, AC-002, AC-006, AC-013, AC-015, AC-007 (secondary)
  **Design:** DES-001, DES-009, DES-010, DES-011, DES-021, DES-022, DES-028, DES-029
  **Changes:** CHG-011
  **Tests:** TEST-013, TEST-014, TEST-015, TEST-016, TEST-017, TEST-018
  **Depends on:** TASK-004, TASK-007

  **Outcome:** the five outcomes of SDD 3.2 all work, citations come only from documents passed to the draft step, and tool or model failures return `status=error`.

  **Inputs:** `rules.filter_docs`, `rules.confidence`, `search_knowledge`, `find_owner`, draft step and fake model.
  **Constraints:** no draft call on escalation; `escalate_human` prints team/area/channel (AS06); top 3 documents only; foreign citation ids dropped; no stack traces in output.
  **Rollback:** restore `workflow.py` from Phase 7.
  **Measurement:** call recorder counts and outcome fields per test.

  **Allowed changes:**
  - `support_copilot/workflow.py`
  - `tests/test_workflow_answer.py`
  - `tests/test_workflow_failure.py`

  **Do not change:** `rules.py`, `tools.py`, the 0.70 cutoff.

  **Implementation steps:**
  1. Write TEST-013 to TEST-018 (red).
  2. Implement the remaining nodes and edges.
  3. Run the checks.

  **Expected artifacts:** the three files above
  **Expected LOC impact:** production +80–120; tests +120–180; confidence: medium; basis: Phase 7 workflow structure; depends on R1 outcome.
  **Required checks:** `uv run pytest tests/test_workflow_answer.py tests/test_workflow_failure.py`; `uv run pytest`
  **Policy evidence:** untrusted LLM output → citation provenance rule enforced and tested; `N/A` for other triggers.
  **Objective-evidence mapping:** AC-001 → TEST-013; AC-002 → TEST-014; AC-006 → TEST-015; AC-013 → TEST-016; AC-015 → TEST-017; AC-007 (secondary) → TEST-018.
  **Test derivation:**

  | TEST ID | AC ID | Test level | Level role | Precondition / controlled data | Trigger | Positive oracle | Negative oracle | Boundary or failure |
  |---|---|---|---|---|---|---|---|---|
  | TEST-013 | AC-001 | integration | Primary | TCK-1001, fake extract and draft outputs | `handle_support_ticket` | ok, escalate false, non-empty response, KB-101 cited, confidence >= 0.70 | no incident result | citation ids limited to passed documents |
  | TEST-014 | AC-002 | integration | Primary | TCK-1002 | same | KB-103 cited | KB-102 absent from citations and from the draft prompt | filter applied before drafting |
  | TEST-015 | AC-006 | integration | Primary | billing ticket (area `billing`), no billing knowledge approved and internal (KB-105 is restricted) | same | `escalate` true, owner "Revenue Cycle Operations" and "#help-revenue-cycle", `escalate_human` output has team, area, channel | draft call count 0, `response` None | restricted KB-105 not used |
  | TEST-016 | AC-013 | contract | Primary | one run per outcome (error, incident, escalation, answer, dependency failure) | collect results | field set equals the contract; `response` set only on an answer; `escalate` true only on escalation | no extra or missing field | all five outcomes covered |
  | TEST-017 | AC-015 | resilience | Primary | tools or fake model that raise or time out | `handle_support_ticket` | `status == "error"`, non-empty `error_message`, `response` None, `escalate` false | no exception escapes; no traceback text in `error_message` | failure at extract, search and draft each tested |
  | TEST-018 | AC-007 | integration | Secondary — proves the below-cutoff edge to escalation, which the pure score test cannot | approved document with a confidence below 0.70 | same | `escalate` true, no draft call | `confidence_score` still reported | cutoff exactly 0.70 does not escalate |

  **Completion evidence:** changed files; red/green commands and exit codes; counts; discovered decisions; remaining uncertainty

**Expected authored LOC:** production +80–120; tests +120–180
**Success criteria:** all six tests pass and `uv run python -m support_copilot.demo` shows the expected outcome for each fixture ticket.
**Commit message:** `feat: complete workflow with confidence gating, escalation and drafting`
**Git:** plan worktree.

### Phase 9 — CLI and demo
**Goal:** the CLI contract of SDD 5.1, and a demo that matches the new result type.
**Size:** S
**Files affected:** `support_copilot/cli.py`, `support_copilot/demo.py`, `tests/test_cli.py`
**Task:**
- [ ] TASK-009 — `python -m support_copilot.cli` and demo update

  **Requirements:** REQ-F-001, REQ-NF-003; AC-011, AC-010 (scan), AC-004 (secondary)
  **Design:** DES-005, DES-015
  **Changes:** CHG-012, CHG-013
  **Tests:** TEST-019, TEST-020, TEST-021
  **Depends on:** TASK-008

  **Outcome:** the CLI accepts `--ticket`, free text and stdin, prints one JSON result, and exits 0, 1 or 2 per the SDD.

  **Inputs:** `handle_support_ticket`, `load_tickets`, the fake model fixture (injected for tests).
  **Constraints:** one JSON object on stdout; diagnostics on stderr; no key in any output; `--ticket` excludes `--title`/`--description`.
  **Rollback:** delete `cli.py` and restore `demo.py`.
  **Measurement:** exit codes and output scans.

  **Allowed changes:**
  - `support_copilot/cli.py`
  - `support_copilot/demo.py`
  - `tests/test_cli.py`

  **Do not change:** the workflow, the result contract.

  **Implementation steps:**
  1. Write TEST-019 to TEST-021 (red).
  2. Implement the CLI and update the demo.
  3. Run the checks.

  **Expected artifacts:** the three files above
  **Expected LOC impact:** production +60–90 / ~10 modified; tests +80–120; confidence: medium; basis: `demo.py:12` and standard `argparse` use.
  **Required checks:** `uv run pytest tests/test_cli.py`; `uv run pytest`
  **Policy evidence:** secrets handling → TEST-020 scans stdout and stderr for a sentinel key value.
  **Objective-evidence mapping:** AC-011 → CLI → TEST-019 → pytest result; AC-010 (scan) → TEST-020; AC-004 (secondary exit code) → TEST-021.
  **Test derivation:**

  | TEST ID | AC ID | Test level | Level role | Precondition / controlled data | Trigger | Positive oracle | Negative oracle | Boundary or failure |
  |---|---|---|---|---|---|---|---|---|
  | TEST-019 | AC-011 | integration | Primary | fake model injected; fixture and free-text inputs | run `main([...])` for `--ticket`, `--title/--description`, `--description -` with stdin | each prints one JSON object; exit 0 for ok | `--ticket` with `--title` exits 2; unknown id exits 1 with `status=error` | stdout is a single JSON object |
  | TEST-020 | AC-010 | security | Primary | env sentinel `ANTHROPIC_API_KEY=sk-test-SENTINEL` | run each path including an error | sentinel absent from stdout and stderr | n/a | logs on stderr contain no ticket text |
  | TEST-021 | AC-004 | integration | Secondary — proves the exit code mapping at the CLI, which the domain test cannot | empty `--description` | run CLI | exit code 1, JSON `status=error` naming `description` | no model call | n/a |

  **Completion evidence:** changed files; red/green commands and exit codes; discovered decisions; remaining uncertainty

**Expected authored LOC:** production +70–100; tests +80–120
**Success criteria:** TEST-019 to TEST-021 pass and `uv run python -m support_copilot.cli --ticket TCK-1003` runs against the fakes in tests.
**Commit message:** `feat: add support copilot CLI`
**Git:** plan worktree.

### Phase 10 — Live checks, traceability gate and docs
**Goal:** the manual live checks, the traceability gate and updated commands.
**Size:** S
**Files affected:** `tests/test_live.py`, `tests/test_traceability.py`, `AGENTS.md`, `CLAUDE.md`
**Task:**
- [ ] TASK-010 — Live performance/trace tests, AC traceability test, command docs

  **Requirements:** REQ-NF-001, REQ-NF-004; AC-009, AC-010 (secondary trace)
  **Design:** DES-019, DES-023, DES-024
  **Changes:** CHG-014, CHG-015
  **Tests:** TEST-022, TEST-023, TEST-024
  **Depends on:** TASK-009

  **Outcome:** `uv run pytest -m live` runs the live checks when a key is set; `uv run pytest` fails if any AC lacks a referencing test; `AGENTS.md` and `CLAUDE.md` list the uv and pytest commands.

  **Inputs:** `docs/requirement/requirements.md` AC ids; all test files; verified commands.
  **Constraints:** live tests skip without `ANTHROPIC_API_KEY`; docs list only commands verified in this run.
  **Rollback:** restore the two docs; delete the two test files.
  **Measurement:** timings per fixture ticket (p95 over 20 runs), LangSmith trace link, traceability test result.

  **Allowed changes:**
  - `tests/test_live.py`
  - `tests/test_traceability.py`
  - `AGENTS.md`
  - `CLAUDE.md`

  **Do not change:** `docs/policy/engineering_constitution.md`, the `requirements.md` ACs.

  **Implementation steps:**
  1. Write TEST-022 to TEST-024; run the traceability test (red until every AC is referenced).
  2. Update `AGENTS.md` and `CLAUDE.md` commands.
  3. Run the offline suite, then the live checks by hand if a key is available.

  **Expected artifacts:** the four files above
  **Expected LOC impact:** production +0; tests +60–90 (live +30–40, traceability +25–40); docs/config +25–40; confidence: medium; basis: `tests/test_starter.py` style and the existing command lists.
  **Required checks:** `uv run pytest`; `uv run pytest tests/test_traceability.py`; `uv run pytest -m live` (manual, needs key)
  **Policy evidence:** evidence cannot be automated for live runs → named human owner records timings and the trace link; observability evidence = LangSmith trace.
  **Objective-evidence mapping:** AC-009 → CLI → TEST-022 → timings; AC-010 (secondary trace) → TEST-024 → trace link; traceability → TEST-023 → pytest result.
  **Test derivation:**

  | TEST ID | AC ID | Test level | Level role | Precondition / controlled data | Trigger | Positive oracle | Negative oracle | Boundary or failure |
  |---|---|---|---|---|---|---|---|---|
  | TEST-022 | AC-009 | performance | Primary | live key, three fixtures, 20 runs each | run the workflow | p95 <= 10 s | skipped (not failed) when no key | per-ticket timings printed |
  | TEST-023 | AC-001..AC-015 | contract | Primary — gate for the plan's traceability requirement, not an AC of its own | `requirements.md` and `tests/` | scan for AC ids | every AC id appears in a test name or docstring | a missing id names the AC in the failure | uses the live requirements file |
  | TEST-024 | AC-010 | end-to-end | Secondary — proves an external trace exists, which the offline scan cannot | live keys, `LANGSMITH_TRACING=true` | run one ticket | a trace for the run exists in LangSmith | key absent from output | skipped without keys |

  **Completion evidence:** changed files; red/green commands and exit codes; timings and trace link (manual); discovered decisions; remaining uncertainty (live checks not run if no key)

**Expected authored LOC:** tests +60–90; docs +25–40
**Success criteria:** the offline suite and traceability test pass; the live checks pass or are recorded as not run; the documented commands were each executed.
**Commit message:** `test: add live checks and AC traceability gate; update commands`
**Git:** plan worktree.

### Final Checkpoint
- [ ] All tests pass (`uv run pytest`)
- [ ] Full feature complete: three fixtures behave per AC-001 to AC-003
- [ ] Traceability test shows every AC referenced
- [ ] Record the commands, exit status and artifacts as `RESULT-*` evidence (allocated by `cg-exec`)
- [ ] Live checks run or explicitly recorded as not run
- [ ] Ready for `cg-review`

## Parallelization

| Category | Tasks | Rule |
|----------|--------|------|
| Safe to parallelize | TASK-003, TASK-005, TASK-006 | No dependency path between them and no shared allowed changes. Only worth doing with separate checkouts (needs git, R3) |
| Must be sequential | TASK-001 → TASK-002; TASK-003 → TASK-004; TASK-007 → TASK-008 → TASK-009 → TASK-010 | Each produces input for the next |
| Needs coordination | TASK-007 | Depends on the result type (002), rules (003), tool wrappers (005) and the extract step and fakes (006); define those interfaces first |

## Coverage Check
- **REQ:** F-001 → T9; F-002 → T2, T6; F-003 → T7; F-003a → T3, T7; F-004 → T7; F-005 → T3, T8; F-006 → T8; F-006a → T4, T8; F-007 → T6, T8; F-008 → T2, T8; F-009 → T5; F-010 → T1; NF-001 → T10; NF-002 → T6, T8; NF-003 → T6, T9; NF-004 → T7, T10; NF-005 → N/A.
- **AC:** 001 → T8 (T4 secondary); 002 → T8; 003 → T7; 004 → T7 (T9 secondary); 005 → T3 (T7 secondary); 006 → T8; 007 → T4 (T8 secondary); 008 → T3; 009 → T10; 010 → T9 (T10 secondary); 011 → T9; 012 → T6; 013 → T8 (T2 secondary); 014 → T5; 015 → T8 (T6 secondary).
- **DES:** 001 → T8; 002 → T7; 003 → T7; 004 → T3, T7; 005 → T9; 006 → T6; 007 → T5; 008 → T3, T4; 009 → T7, T8; 010 → T7, T8; 011 → T8; 012–014 → T2; 015 → T6, T9; 016 → T7; 017 → T6; 018 → T1; 019 → T6, T10; 020 → T3; 021 → T8; 022 → T6, T8; 023 → T7, T10; 024 → T1, T6, T10; 025–032 (decisions) → the tasks implementing the decision above.

## TODO List (ordered)
- [x] Phase 1: Tooling and dependencies
- [x] Phase 2: Output contract and types
- [x] Phase 3: Area detection and document filter
- [x] Phase 4: Confidence score and calibration
- [x] Phase 5: Fixture tool wrappers
- [ ] Phase 6: LLM adapter and test doubles
- [ ] Phase 7: Workflow: validation, extraction, area, incident stop
- [ ] Phase 8: Workflow: search, escalate, draft, failures
- [ ] Phase 9: CLI and demo
- [ ] Phase 10: Live checks, traceability gate and docs
