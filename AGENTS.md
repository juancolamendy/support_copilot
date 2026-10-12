# AGENTS.md

Agent learning journal for the Product Support Copilot (Python starter). See `CLAUDE.md` for architecture and commands.

## Project Interface

### Commands
- Install / development: N/A (stdlib only, Python >= 3.11); demo: `python3 -m support_copilot.demo`
- Unit tests: `python3 -m unittest discover -s tests`
- Integration tests: N/A (no integration suite; everything runs against local fixtures)
- Types: N/A (no type checker configured)
- Lint / formatting: N/A (ruff is configured in `pyproject.toml` but is not a declared dependency and was not verified)

### Architecture
- `copilot.py` depends on the Protocols in `types.py`, never on concrete `FixtureTools`.
- Fixture JSON is read only via `fixture_store.py`; data lives in `../fixtures/`.
- Public API or event changes require a compatibility decision and migration note.

### Safety
- Never print or commit secrets, credentials, customer data, or raw production feeds.
- Interview material is confidential and all data is synthetic; do not publish or reuse it.
- New runtime dependencies require plan justification and review approval.
- Never weaken, delete, skip, or rewrite tests merely to make a gate pass.

### Workflow
- Multi-file changes require an approved design and plan.
- Run the smallest relevant checks during implementation and all plan-required gates before completion.
- Report exact commands and outcomes; never claim success without evidence.

## Governance

Read and comply with `docs/policy/engineering_constitution.md`.
Policy changes require explicit human approval.

## Workflow Overview

This project uses the `cg-*` command workflow. Each command maps to a phase:

| Phase | Command | Purpose |
|-------|---------|---------|
| Ideate | `/cg-ideate` | Refine vague ideas before writing any requirements |
| Research | `/cg-research` | Ground decisions in current best practices |
| Analysis | `/cg-analysis` | Extract and map requirements to architectural implications |
| Design | `/cg-design` | Produce a Software Design Document (SDD) |
| Adversarial Review | `/cg-design-adv` | Stress-test the SDD for flaws |
| UI options | `/cg-ui-options` | HTML alternatives for bounded UI; pick before coding |
| Plan | `/cg-plan` | Break the SDD into one or more max-ten-phase, TDD-enforced plan artifacts |
| Execute | `/cg-exec <N>` | Implement one phase at a time |
| Review | `/cg-review` | Adversarial audit for correctness, security, architecture |
| Debug | `/cg-debug` / `/cg-debug-adv` / `/cg-debug-inline` | RCA → optional plan stress-test → exec, or in-session Apply Fix (+ optional Pass 2) |
| Security | `/cg-security` | OWASP audit and hardening |
| Performance | `/cg-perf` | Measure, identify bottlenecks, optimize |
| Docs | `/cg-docs` | Write ADRs and update project documentation |

Invoke as `/name` or `$name`. Same free text after the name.

Run `/cg-help` or `$cg-help` at any time to get a decision tree for which command to use.

## Core Operating Behaviors

These behaviors apply at all times and are non-negotiable.

### Surface Assumptions

Before starting any non-trivial task, state assumptions explicitly:

```
ASSUMPTIONS I'M MAKING:
1. [assumption about requirements]
2. [assumption about architecture]
3. [assumption about scope]
→ Correct me now or I'll proceed with these.
```

Do not silently fill in ambiguous requirements.

### Manage Confusion Actively

When encountering inconsistencies, conflicting requirements, or unclear specs:
1. STOP. Do not proceed with a guess.
2. Name the specific confusion.
3. Present the tradeoff or ask the clarifying question.
4. Wait for resolution before continuing.

Bad: Silently picking one interpretation and hoping it is right.
Good: "I see X in the spec but Y in the existing code. Which takes precedence?"

### Push Back When Warranted

When an approach has clear problems:
- Point out the issue directly.
- Quantify the downside when possible ("this adds ~200ms latency" not "this might be slower").
- Propose an alternative.
- Accept the human's decision if they override with full information.

Sycophancy is a failure mode. "Of course!" followed by implementing a bad idea helps no one.

### Enforce Simplicity

Before finishing any implementation, ask:
- Can this be done in fewer lines?
- Are these abstractions earning their complexity?
- Would a staff engineer say "why didn't you just..."?

Three similar lines of code is better than a premature abstraction.

### Commit

There is no separate commit skill. After `/cg-exec` or `/cg-exec-inline`, one atomic commit is part of the phase once tests pass and self-review is clean. Otherwise, commit only when the user asks. (This directory is not currently a git repository.)

When committing:

1. Inspect `git status`, `git diff HEAD`, and recent `git log`. Match existing message style.
2. **Ticket prefix primary.** If a ticket ID is inferable (branch, plan, conversation) — `{TICKET-1234}`, `{FEAT-1234}`, `{BUG-1234}`, or `{PREFIX}-{NUMBER}` — the message **must** start with it. Never invent a ticket ID.
3. **Conventional type next** (`feat` / `fix` / `refactor` / `test` / `docs` / `chore`). The rest of the message explains **why**, not a file list.
4. `git add` only the files intended for this commit. Do not stage unrelated dirty files or secrets (`.env`, credentials, keys, vault material).
5. Pass the message via HEREDOC. Do not use a one-line `-m` that mangles formatting.

~~~~bash
git add <intended files>
git commit -m "$(cat <<'EOF'
{TICKET-1234}: feat: <why this change>

EOF
)"
~~~~

Fallback when no ticket is inferable: omit the prefix and start with `<type>:`.

- Never `git push` (or force-push) unless the user explicitly asked in this turn.
- Never skip hooks (`--no-verify`, `--no-gpg-sign`, or equivalent) unless the user explicitly asked in this turn.
- If a hook rejects the commit, fix the issue and create a **new** commit. Do not `--amend` unless the user asked and HEAD is your unpushed commit.

## Session Start

- Read and process all files inside `docs/project/` and `docs/memory/` at the beginning of each session to ensure complete context before providing assistance.
- Read and comply with `docs/policy/engineering_constitution.md` before planning or implementing work.
- Ask "do you have any questions before I proceed?" when starting a new task.

## Research

- Describe the tech stack, folder structure, coding conventions, and any anti-patterns to avoid before writing any code.

## Analysis / Design

- Before writing any code, describe your approach and wait for explicit approval.
- Ask clarifying questions if requirements are ambiguous — do not assume.

## Planning

- If a task requires changes to more than 3 files, stop and break it into smaller tasks first.

## Implementation

- When there is a bug, start by writing a failing test that reproduces it, then fix the code until the test passes.
- After writing code, list what could break and suggest tests to cover those cases.
- Keep functions small and simple — maximum 70 lines of code per function.

## Feedback and Corrections

- When the user says something is wrong, ask clarifying questions before rewriting anything.
- Every time the user corrects you, add a new rule to this file (`AGENTS.md`) so it never happens again.

## Project Files

- Proactively suggest updates to `docs/project/` files when new information emerges.
- Update files in `docs/project/` when discovering new project patterns, after implementing significant changes, or when the user requests it.
