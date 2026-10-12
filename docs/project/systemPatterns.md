# System Patterns

## Components (`support_copilot/`)
- `types.py`: frozen dataclasses and the `CopilotTools` / `LanguageModel` Protocols. The copilot depends on these, not on concrete fixtures.
- `copilot.py`: `handle_support_ticket`, the logic to implement.
- `tools.py`: `FixtureTools` (keyword-scored knowledge search, owner lookup, active incidents).
- `mock_model.py`: deterministic fake LLM that echoes the first `CONTEXT:` prompt line.
- `fixture_store.py`: loads `../../fixtures/*.json` (camelCase to snake_case).
- `demo.py`: runs every fixture ticket and prints the decision as JSON.

## Data flow
ticket -> tools (search / owner / incidents) -> decision logic (optionally model) -> `SupportDecision(action, message, evidence, owner, notes)`.

## Known pitfalls
- `search_knowledge` does not filter by `status` or `access`; deprecated/draft/restricted docs can be returned.
- Conflicting docs exist (KB-102 deprecated vs KB-103 approved).
- The mock model does no reasoning.
