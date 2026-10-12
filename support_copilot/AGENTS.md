# AGENTS.md: support_copilot

- `copilot.py` depends only on the `CopilotTools` / `LanguageModel` Protocols from `types.py`; never import `FixtureTools` there.
- `tools.py` search does not filter `status` or `access`; filter in the copilot (or tools) before trusting a hit.
- `mock_model.py` only echoes the first `CONTEXT:` line; it does no reasoning.
- Fixture JSON is camelCase; map to snake_case in `fixture_store.py` only.
- Fixtures live outside this package at `../../fixtures/`.
