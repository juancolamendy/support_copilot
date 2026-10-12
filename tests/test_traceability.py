"""Acceptance-criteria traceability gate for TASK-010 (REQ-NF-004, DES-024).

Fails when an AC in requirements.md has no test that names it, or when a test
names an AC that does not exist. Run: uv run pytest tests/test_traceability.py
"""

from __future__ import annotations

import re
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REQUIREMENTS = TESTS_DIR.parent / "docs" / "requirement" / "requirements.md"
AC_ID = re.compile(r"AC-\d{3}")


def _defined_acceptance_criteria() -> set[str]:
    text = REQUIREMENTS.read_text(encoding="utf-8")
    return set(re.findall(r"^- \[(AC-\d{3})\]", text, flags=re.MULTILINE))


def _referenced_acceptance_criteria() -> set[str]:
    referenced: set[str] = set()
    for path in TESTS_DIR.glob("test_*.py"):
        if path.name == Path(__file__).name:
            continue
        referenced |= set(AC_ID.findall(path.read_text(encoding="utf-8")))
    return referenced


def test_023_requirements_define_acceptance_criteria() -> None:
    """[TEST-023][REQ-NF-004][DES-024][TASK-010] the gate is not vacuous."""
    assert len(_defined_acceptance_criteria()) >= 15


def test_023_every_acceptance_criterion_is_referenced_by_a_test() -> None:
    """[TEST-023][REQ-NF-004][DES-024][TASK-010] no AC without a verifier."""
    missing = sorted(_defined_acceptance_criteria() - _referenced_acceptance_criteria())

    assert not missing, f"acceptance criteria with no test naming them: {missing}"


def test_023_tests_only_name_acceptance_criteria_that_exist() -> None:
    """[TEST-023][REQ-NF-004][DES-024][TASK-010] typos in AC ids are caught."""
    unknown = sorted(_referenced_acceptance_criteria() - _defined_acceptance_criteria())

    assert not unknown, f"tests name acceptance criteria that do not exist: {unknown}"
