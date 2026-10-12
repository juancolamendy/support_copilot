# Project Brief

## Goal
Build a working prototype of a **Product Support Copilot** (Talkiatry interview exercise, 60-minute timebox). Given an incoming support ticket, it helps a support expert decide how to handle it and provides a useful response or next step.

## Core requirements
- Entry point: `handle_support_ticket(ticket, tools) -> SupportDecision` in `support_copilot/copilot.py`.
- Decision actions: `respond`, `clarify`, `escalate`.
- Runs fully locally; no external credentials or real Jira/Notion/model integrations.
- Demonstrate behavior on the supplied fixture tickets and add the most valuable tests/evals.

## Scope
- In: thin end-to-end copilot, tests/evals, explaining assumptions and tradeoffs.
- Out: UI, production deployment, real integrations.
- Types and interfaces may be changed if that supports the approach.

## Constraints
- Python 3.11+, stdlib only so far.
- Interview material is confidential (`../NOTICE.md`); all data is synthetic.
- Source of truth for the task: `../README.md`.
