# Traceability Index

Links and IDs only. Source artifacts (requirements, SDD, plan) remain authoritative.

| Requirement / AC | Design | Task | Change | Code link | Test | Result |
|---|---|---|---|---|---|---|
| REQ-F-010 / none (constraint) | DES-018, DES-024 | TASK-001 | CHG-001 | `pyproject.toml` (`dependencies`, `[dependency-groups]`, `[tool.pytest.ini_options]`) | TEST-001 — `tests/test_tooling.py::test_001_runtime_dependencies_import`, `::test_001_live_marker_is_registered` | RESULT-001, RESULT-002, RESULT-003 — plan Phase 1 evidence |
| REQ-F-008 / AC-013 (secondary) | DES-013, DES-014 | TASK-002 | CHG-002 | `support_copilot/types.py` (`SupportResult`, `Citation`, `WorkflowState`) | TEST-002 — `tests/test_types.py::test_002_support_result_has_exactly_the_contract_fields` and 8 more | RESULT-004, RESULT-005, RESULT-006 — plan Phase 2 evidence |
| REQ-F-002, REQ-F-007 / AC-013 (secondary) | DES-012 | TASK-002 | CHG-002 | `support_copilot/types.py` (`TicketDetails`, `DraftAnswer`) | TEST-002 — `tests/test_types.py::test_002_ticket_details_requires_a_summary`, `::test_002_draft_answer_requires_a_response` | RESULT-005 — plan Phase 2 evidence |
| REQ-F-008 / AC-013 (secondary) | DES-013 | TASK-002 | CHG-003 | `support_copilot/copilot.py` (`handle_support_ticket` placeholder) | TEST-002 — `tests/test_types.py::test_002_placeholder_handler_returns_an_error_result` | RESULT-006 — plan Phase 2 evidence |
| REQ-F-003a / AC-005 | DES-004, DES-008, DES-026 | TASK-003 | CHG-004 | `support_copilot/rules.py` (`detect_area`) | TEST-003 — `tests/test_rules.py::test_003_detect_area_*` | RESULT-007, RESULT-008, RESULT-009 — plan Phase 3 evidence |
| REQ-F-005 / AC-008 | DES-020, DES-028 | TASK-003 | CHG-004 | `support_copilot/rules.py` (`filter_docs`) | TEST-004 — `tests/test_rules.py::test_004_filter_docs_*` | RESULT-007, RESULT-008, RESULT-009 — plan Phase 3 evidence |
| REQ-F-006a / AC-007 | DES-008, DES-027 | TASK-004 | CHG-005 | `support_copilot/rules.py` (`confidence`, `CONFIDENCE_THRESHOLD`) | TEST-005 — `tests/test_confidence.py::test_005_*` | RESULT-010, RESULT-011, RESULT-012 — plan Phase 4 evidence |
| REQ-F-006a / AC-001 (secondary) | DES-027 | TASK-004 | CHG-005 | `support_copilot/rules.py` (`confidence`) | TEST-006 — `tests/test_confidence.py::test_006_*` | RESULT-011, RESULT-012 — plan Phase 4 evidence |
