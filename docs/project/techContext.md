# Tech Context

- Language: Python >= 3.11 (`pyproject.toml`); no runtime dependencies.
- Async: tools and model are `async`; the demo uses `asyncio.run`.
- Tests: stdlib `unittest` in `tests/`.
- Lint: `[tool.ruff]` line-length 88 in `pyproject.toml`; ruff is not a declared dependency and was not verified as installed.
- Data: JSON fixtures in `../fixtures/` (`tickets`, `knowledge`, `ownership`, `incidents`), shared with the TypeScript starter in `../typescript/`.
- No git repository at this directory.

## Commands (from `../README.md`)
- `python3 -m unittest discover -s tests`
- `python3 -m support_copilot.demo`
