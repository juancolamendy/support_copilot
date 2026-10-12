from __future__ import annotations

from .types import ModelResponse


class MockLanguageModel:
    """A deterministic stand-in for an external model."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system: str, prompt: str) -> ModelResponse:
        self.calls.append((system, prompt))
        context = next(
            (
                line.removeprefix("CONTEXT:").strip()
                for line in prompt.splitlines()
                if line.strip().startswith("CONTEXT:")
            ),
            "The mock model did not receive recognizable context.",
        )
        return ModelResponse(
            text=context,
            model="local-deterministic-mock",
            input_characters=len(system) + len(prompt),
        )
