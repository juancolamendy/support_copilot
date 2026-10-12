# Requirements

## Problem and Expected Outcome
- Problem: Tier 1 support teams submit product questions via Jira. One product-support expert manually reviews each ticket, searches docs, responds, or escalates. This is slow, depends on one person's time and institutional knowledge, and is inconsistent.
- Expected outcome: Reduced time-to-handle per ticket. Each ticket is turned into one of: a cited draft response, a request for clarification, a stop (already-reported incident), or a human escalation routed to the right team/channel. The support expert keeps final judgment.

## Objectives and Success Metrics
- [OBJ-001] Objective: Reduce the time a support expert spends per ticket.
  - Success metric: All three supplied fixture tickets reach the expected outcome (AC-001 to AC-003) within the 10 s latency budget (AC-009). Time saved is argued, not measured, in v1.
- [OBJ-002] Objective: Never present an unsupported answer as authoritative.
  - Success metric: 100% of `ok` responses carry at least one citation from an approved, non-restricted document (see Q-004).

## Scope
- In scope (v1): CLI app; stateless single-ticket flow; ticket detail extraction and required-field validation; active-incident check; knowledge search; escalation with owner routing; cited draft response with confidence score; fixture-based deterministic unit tests (including extraction); LangSmith observability.
- Out of scope (v1, added after manual testing): LLM-as-judge evaluation of the drafted response.
- Out of scope (v2): `reasoning` output field; conversation/thread state (no `thread_id` / `conversation_id`); real Jira, Notion, or model-provider integrations; UI; production deployment.

## Actors
- [ACT-001] Support expert: reviews copilot output, decides how to handle the ticket, retains final judgment.
- [ACT-002] Tier 1 support agent: submits tickets and receives clarification requests or responses.
- [ACT-003] Owning team (e.g. Portal Platform): receives escalations via its channel.

## User Stories
- [US-001] As ACT-001, I want a cited draft response for answerable tickets so that I spend less time searching docs.
- [US-002] As ACT-002, I want to be asked for missing information so that the ticket can be processed.
- [US-003] As ACT-001, I want tickets matching an already-reported incident to stop early so that no redundant work or conflicting answer is produced.
- [US-004] As ACT-001, I want unanswerable tickets escalated to the right team and channel so that they reach a human quickly.

## Functional Requirements
- [REQ-F-001] CLI: `--ticket <id>` loads a fixture ticket, or `--title`/`--description` (or stdin) supplies free text (Q-008). Input: `question` (text) and `metadata`; the CLI accepts one ticket per invocation, with no conversation state.
- [REQ-F-002] Extract `ticket_details` from the ticket description using an LLM.
- [REQ-F-003a] Determine the ticket `area` deterministically (no LLM) by matching terms derived from ownership.json area names against the ticket title and description (Q-006, Q-012). No match means clarify.
- [REQ-F-003] Validate that required information is present; the ticket description is required (AS04). If missing, stop the flow with `status = error` and an `error_message` listing the missing fields; no drafting call, `escalate = false`. This is the clarification request (AS01, Q-013).
- [REQ-F-004] Look up the ticket in active incidents (deterministic, via tool). If a non-resolved incident exists in the ticket's area, end the flow: `status = ok`, `escalate = false`, no drafted response, output carries the incident id/status/summary and the owner's team/channel (Q-002).
- [REQ-F-005] If no incident matches, search knowledge (deterministic, via tool). Discard documents that are not `approved` and `internal` before drafting or citing (Q-004).
- [REQ-F-006] If the retrieved knowledge list is empty (after the Q-004 filter, to confirm), escalate to a human (AS02). Escalation is deterministic and makes no LLM call. Use ownership data to determine team/area/channel; `escalate_human` prints team/area/channel (AS06). When escalating, `escalate = true` and no response is generated (AS03).
- [REQ-F-006a] Compute `confidence_score` deterministically from retrieval results. If it is below 70%, escalate as in REQ-F-006 (Q-003).
- [REQ-F-007] Otherwise draft a response with an LLM, grounded in the retrieved documents, and return `citations` and `confidence_score`.
- [REQ-F-008] Output: `response` (text), `citations`, `confidence_score`, `status` (`ok` | `error`), `error_message`, escalate flag (AS03). `reasoning` is v2.
- [REQ-F-009] Each fixture (tickets, knowledge, ownership, incidents) is exposed to the workflow as a tool.
- [REQ-F-010] The workflow is built with LangChain/LangGraph (`create_agent` API). Treated as a design constraint; verified by review, not by a dedicated AC.

## Non-functional Requirements
- [REQ-NF-001] Performance: one ticket completes in at most 10 s at p95 with the live provider (Q-009).
- [REQ-NF-002] Availability / Reliability: A tool or LLM failure yields `status = error` with `error_message`.
- [REQ-NF-003] Security / Privacy: API keys are read from the environment only and never committed or printed. (Q-004 resolved: only approved, internal documents are used). All data is synthetic and the interview material is confidential.
- [REQ-NF-004] Observability: LangSmith for tracing and evaluation (AS07). LangSmith and the real LLM provider need network and API keys from the environment (Q-001, Q-010).
- [REQ-NF-005] Compliance: N/A (no AC; synthetic data only) for this prototype, with a note that real deployment would need PHI handling review.

## Assumptions and Constraints
- Assumption: AS01 to AS04, AS06 and AS07 as listed in the specification. AS05 is absent from the specification (numbering gap).
- Assumption: confidence is retrieval-based and 70% is the escalation cutoff (Q-003); the formula is a design decision.
- [CON-001] The README says everything runs locally with no credentials; v1 deliberately departs from this by using a real LLM provider and LangSmith (Q-001 resolved). Credentials come from the environment, are never committed, and provider choice and offline behavior are open (Q-010).
- [CON-002] Python >= 3.11; LLM provider is Anthropic Claude via langchain-anthropic. The starter is stdlib-only, so LangChain/LangGraph/LangSmith are new dependencies.
- [CON-003] 60-minute interview timebox.

## Edge Cases & Failure Modes
- Missing ticket description or required fields: clarify.
- Knowledge hit is deprecated, draft or restricted (e.g. KB-102 vs KB-103): dropped; if nothing remains, escalate.
- Incident exists but in a different area than the ticket's real topic: matching rule open (Q-002).
- Confidence below 70%: escalate, no response.
- No owner found for the area: escalate without channel (to decide).

## Risks
- [RISK-001] Real provider and LangSmith break the README's "no credentials, runs locally" rule; the demo or tests fail where keys are missing. Mitigation: Q-010.
- [RISK-002] An LLM-based extraction step may add latency and error without adding value on short tickets. Mitigation: unit tests with fixtures.
- [RISK-003] Stale or conflicting documents produce wrong answers. Mitigation: Q-004.

## Open Questions
- [Q-001] Status: Resolved
  - Question: Which LLM runtime and observability setup does v1 use, given the no-credentials constraint?
  - Option 1: LangChain/LangGraph around the provided `MockLanguageModel`; LangSmith optional and off by default — Recommended: offline and deterministic.
  - Option 2: Real provider through an API key from the environment, with LangSmith on — realistic quality, needs credentials and network.
  - Option 3: Plain Python with the `LanguageModel` Protocol — simplest, departs from the specified stack.
  - Answer: Option 2. Real provider with LangSmith on.
  - Affects: REQ-F-002, REQ-F-007, REQ-F-010, REQ-NF-004, CON-001
- [Q-010] Status: Resolved
  - Question: How do unit tests and evals run without credentials, and which provider is used?
  - Option 1: Mock for tests, live for evals — Recommended.
  - Option 2: Everything live.
  - Option 3: Skip tests if no key.
  - Answer: Free-form. Unit tests are deterministic, including the extraction step. Evaluation applies only to the drafted response. v1 ships without evals; evals are added after manual testing. Provider not stated (see Q-011).
  - Affects: REQ-F-002, REQ-F-007, AC (pending), Scope
- [Q-011] Status: Resolved
  - Question: Which LLM provider and model does v1 call?
  - Option 1: Anthropic Claude via langchain-anthropic — Recommended.
  - Option 2: OpenAI via langchain-openai.
  - Option 3: Provider-agnostic via init_chat_model.
  - Answer: Option 1. Anthropic Claude, key from `ANTHROPIC_API_KEY`; model name configurable.
  - Affects: REQ-F-002, REQ-F-007, CON-002
- [Q-002] Status: Resolved
  - Question: What does the output contain when a reported incident matches, and how is a match decided?
  - Option 1: Stop with incident link — Recommended.
  - Option 2: Stop, minimal output.
  - Option 3: Stop, but still draft.
  - Answer: Option 1. Match = any non-resolved incident in the ticket's area. Output: `status = ok`, `escalate = false`, no drafted response, plus the incident id/status/summary and the owner's team/channel.
  - Affects: REQ-F-004, REQ-F-008, US-003
- [Q-003] Status: Resolved
  - Question: What is the 70% confidence score for, and how is it computed?
  - Option 1: Retrieval-based, 70% cutoff — Recommended.
  - Option 2: LLM self-reported.
  - Option 3: Report only, no gating.
  - Answer: Option 1. Deterministic score from the top approved, internal hit (normalization formula to be set in design). Score below 70% escalates instead of drafting; the LLM does not grade itself.
  - Affects: REQ-F-006, REQ-F-007, REQ-F-008
- [Q-004] Status: Resolved
  - Question: How are deprecated, draft and restricted documents treated in search results?
  - Option 1: Approved + internal only — Recommended.
  - Option 2: Approved only, restricted flagged.
  - Option 3: Pass all, let the LLM weigh.
  - Answer: Option 1. Only `status = approved` and `access = internal` documents may be used or cited; others are dropped before drafting. If none remain, escalate (REQ-F-006).
  - Affects: REQ-F-005, REQ-F-006, REQ-F-007, AC (pending)
- [Q-005] Status: Resolved (follow-up Q-013)
  - Question: What counts as "missing required information" (triggering a clarification request)?
  - Option 1: Description + detectable area — Recommended.
  - Option 2: Also require requester role.
  - Option 3: Description only.
  - Answer: Free-form. Stop the flow if required data is missing. Escalation uses no LLM. If the retrieved knowledge list has 0 records, escalate. The exact required-field set was not stated; working assumption is a non-empty description (AS04) and a detectable area (Q-012). The stop output is open (Q-013).
  - Affects: REQ-F-003, REQ-F-006, REQ-F-008
- [Q-013] Status: Resolved
  - Question: What does the stop-on-missing-data output look like?
  - Option 1: status=error + missing list — Recommended.
  - Option 2: status=ok + clarification text.
  - Option 3: Raise an exception.
  - Answer: Option 1. `status = error`, `error_message` names the missing fields, `escalate = false`, no response, no drafting call; the CLI prints it and exits non-zero. This is how AS01's clarification is delivered.
  - Affects: REQ-F-003, REQ-F-008, US-002
- [Q-006] Status: Resolved (follow-up Q-012)
  - Question: How is the ticket area determined for incident and ownership lookup?
  - Option 1: LLM extracts area — Recommended.
  - Option 2: Deterministic keyword rules.
  - Option 3: Derived from top knowledge hit.
  - Answer: Free-form. No LLM: load the JSON fixtures and extract the area deterministically using a key/value dict. Source of the dict is open (Q-012).
  - Affects: REQ-F-002, REQ-F-004, REQ-F-006
- [Q-012] Status: Resolved
  - Question: Where does the key/value dict for deterministic area detection come from?
  - Option 1: Derive from ownership.json — Recommended.
  - Option 2: Hand-written keyword dict.
  - Option 3: Both, dict overrides.
  - Answer: Option 1. Terms derived from `area` names in ownership.json (e.g. patient-portal -> patient, portal) matched against ticket title and description. No area match means ask for clarification (AS01).
  - Affects: REQ-F-003, REQ-F-004, REQ-F-006
- [Q-007] Status: Resolved (deferred)
  - Question: What does the LLM-as-judge evaluate, and on what dataset?
  - Answer: Deferred by the Q-010 answer. Evaluation covers only the drafted response; v1 ships without evals and they are added after manual testing. Dataset and judge criteria to be defined then.
  - Affects: Scope, REQ-NF-004
- [Q-008] Status: Resolved
  - Question: CLI shape: single ticket by id from fixtures, free text, or all tickets?
  - Option 1: Ticket id or free text — Recommended.
  - Option 2: Fixture ticket id only.
  - Option 3: Free text only.
  - Answer: Option 1. `--ticket <id>` loads a fixture ticket; `--title`/`--description` (or stdin) accepts free text. One stateless ticket per run; prints JSON of the output fields.
  - Affects: REQ-F-001, REQ-F-008
- [Q-009] Status: Resolved
  - Question: What measurable target defines success for "reduce time", and is there a latency budget?
  - Option 1: Outcome correctness, latency budget — Recommended.
  - Option 2: Fixtures only, no latency target.
  - Option 3: Baseline time comparison.
  - Answer: Option 1. Correct outcomes on the three fixture tickets plus a per-ticket latency budget of 10 s (p95, live provider). Time saved is argued, not measured, in v1.
  - Affects: OBJ-001, REQ-NF-001, AC-001 to AC-003, AC-009

## Acceptance Criteria
- [AC-001] Given fixture ticket TCK-1001, when the flow runs, then it returns `status = ok`, `escalate = false`, a non-empty response and a citation to KB-101 (covers REQ-F-005, REQ-F-007, US-001).
  - Observable boundary: domain service / CLI output
  - Pass/fail rule: output JSON has `status == "ok"`, `escalate == false`, `citations` contains `KB-101`, and `confidence_score >= 0.70`.
  - Objective evidence: automated test result against the fixtures; response text quality is judged later by the evals, not here.
- [AC-002] Given fixture ticket TCK-1002, when the flow runs, then it cites KB-103 and never KB-102 (covers REQ-F-005, Q-004).
  - Observable boundary: domain service / CLI output
  - Pass/fail rule: `citations` contains `KB-103` and does not contain `KB-102`; `status == "ok"`.
  - Objective evidence: automated test result against the fixtures.
- [AC-003] Given fixture ticket TCK-1003, when the flow runs, then it stops at the active incident without a response (covers REQ-F-004, US-003).
  - Observable boundary: domain service / CLI output
  - Pass/fail rule: `status == "ok"`, `escalate == false`, `response` is empty, the output includes incident `INC-2041` and owner team `Care Access Engineering` with channel `#help-care-access`; no knowledge search and no drafting LLM call is made.
  - Objective evidence: automated test result; call record showing zero knowledge-search and zero drafting calls.
- [AC-004] Given a ticket with an empty description, when the flow runs, then it stops with an error naming the missing field (covers REQ-F-003, US-002).
  - Observable boundary: domain service / CLI output / exit code
  - Pass/fail rule: `status == "error"`, `error_message` contains `description`, `escalate == false`, no response, no drafting LLM call; CLI exit code is non-zero.
  - Objective evidence: automated test result.
- [AC-005] Given a ticket whose text matches no area in ownership.json, when the flow runs, then it stops with an error naming the area (covers REQ-F-003a, Q-012).
  - Observable boundary: domain service / CLI output
  - Pass/fail rule: `status == "error"`, `error_message` contains `area`, no incident or knowledge call is made.
  - Objective evidence: automated test result.
- [AC-006] Given a ticket in a known area with no incident and zero approved, internal knowledge hits, when the flow runs, then it escalates (covers REQ-F-006, AS02, AS03, US-004).
  - Observable boundary: domain service / CLI output
  - Pass/fail rule: `escalate == true`, `response` is empty, output carries the area's owner team and channel from ownership.json, and `escalate_human` printed team/area/channel; no drafting LLM call and no LLM call for escalation.
  - Objective evidence: automated test result using a fixture ticket variant, e.g. a billing ticket with no billing knowledge (to be confirmed against the knowledge fixture).
- [AC-007] Given retrieval whose top approved hit scores below 70%, when the flow runs, then it escalates as in AC-006 (covers REQ-F-006a, Q-003).
  - Observable boundary: domain service
  - Pass/fail rule: `confidence_score < 0.70` leads to `escalate == true` and no response; the score is identical across repeated runs on the same input.
  - Objective evidence: automated test result; the formula is documented in the design.
- [AC-008] Given any knowledge result set containing deprecated, draft or restricted documents, when the flow runs, then none is cited or passed to the drafting model (covers REQ-F-005, Q-004).
  - Observable boundary: domain service
  - Pass/fail rule: every id in `citations` and in the drafting prompt belongs to a document with `status == "approved"` and `access == "internal"`.
  - Objective evidence: automated test result with a fixture set including KB-102.
- [AC-009] Given the live provider, when each fixture ticket runs, then it completes within the latency budget (covers REQ-NF-001, Q-009).
  - Observable boundary: CLI
  - Pass/fail rule: wall-clock time per ticket is at most 10 s at p95 over repeated runs.
  - Objective evidence: recorded timings; LangSmith trace durations.
- [AC-010] Given the ticket flow runs with the API key set, when it completes, then a LangSmith trace exists and the key is absent from all output (covers REQ-NF-003, REQ-NF-004).
  - Observable boundary: external effect / CLI output
  - Pass/fail rule: a trace for the run is present in the LangSmith project; stdout, stderr and traces do not contain the API key value.
  - Objective evidence: LangSmith trace record and a test that scans the CLI output.
- [AC-011] Given the CLI, when run with `--ticket <id>`, with `--title`/`--description`, or with `--description -` and stdin, then each mode produces one JSON result and the exit code reflects `status` (covers REQ-F-001).
  - Observable boundary: CLI
  - Pass/fail rule: exit code 0 for `status == "ok"`, 1 for `status == "error"` (including an unknown ticket id), 2 for invalid argument combinations; stdout is a single JSON object.
  - Objective evidence: automated test result.
- [AC-012] Given a canned model response, when the extract step runs, then it returns a valid `TicketDetails` or a `status = error` for malformed output (covers REQ-F-002).
  - Observable boundary: domain service
  - Pass/fail rule: `summary`, `symptoms` and `product_terms` are present with the declared types; malformed output yields an error result, not an exception.
  - Objective evidence: automated test result.
- [AC-013] Given each of the five outcomes, when the flow completes, then the result contains every `SupportResult` field with the declared type (covers REQ-F-008).
  - Observable boundary: domain service
  - Pass/fail rule: field set equals the contract exactly; `response` is non-null only on an answer, `escalate` is true only on escalation.
  - Objective evidence: automated test result.
- [AC-014] Given the fixture tools, when each of tickets, incidents, knowledge and ownership is requested through its tool wrapper, then it returns the fixture records (covers REQ-F-009).
  - Observable boundary: domain service
  - Pass/fail rule: the returned ids equal the fixture ids (e.g. INC-2041 for scheduling, KB-103 for an invitation query, owner team "Portal Platform" for patient-portal).
  - Objective evidence: automated test result.
- [AC-015] Given a tool or model that raises or times out, when the flow runs, then it returns `status = error` with a non-empty `error_message` and no response (covers REQ-NF-002).
  - Observable boundary: domain service
  - Pass/fail rule: `status == "error"`, `error_message` non-empty, `response is None`, `escalate == false`; no exception escapes.
  - Objective evidence: automated test result.
