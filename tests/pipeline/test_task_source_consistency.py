"""Guardrails for the public task source of truth.

The root ``tasks.md`` is the public-safe board agents must consult
before picking up work. These tests fail if the board still points to
already-shipped work or stops referencing the current non-manual
handoff spec.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TASKS_PATH = REPO_ROOT / "tasks.md"
NON_MANUAL_SPEC = "docs/NON-MANUAL-IMPLEMENTATION-SPECS.md"

# The Hamburg merge landed as commit 99930d1 on `main`. The matching
# task should live under "Done" or be re-scoped — it must not still
# appear as an *active* checkbox.
STALE_ACTIVE_PHRASE = "Ship the Hamburg worktree"


def _split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = "_preamble"
    buffer: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections[current] = "\n".join(buffer)
            current = line[3:].strip().lower()
            buffer = []
        else:
            buffer.append(line)
    sections[current] = "\n".join(buffer)
    return sections


def test_tasks_md_exists() -> None:
    assert TASKS_PATH.exists(), "root tasks.md is the canonical public task source"


def test_active_section_does_not_resurface_shipped_hamburg_work() -> None:
    sections = _split_sections(TASKS_PATH.read_text())
    active = sections.get("active", "")
    # Allow the phrase elsewhere (Done section), but not as an open task.
    for line in active.splitlines():
        if "- [ ]" in line and STALE_ACTIVE_PHRASE in line:
            raise AssertionError(
                f"Active task list still points to shipped Hamburg work: {line.strip()}"
            )


def test_tasks_md_references_non_manual_spec_while_tickets_are_open() -> None:
    text = TASKS_PATH.read_text()
    assert NON_MANUAL_SPEC in text, (
        "tasks.md should link to docs/NON-MANUAL-IMPLEMENTATION-SPECS.md "
        "so agents discover the ready-for-handoff tickets"
    )
    assert (REPO_ROOT / NON_MANUAL_SPEC).exists(), (
        "the non-manual handoff spec linked from tasks.md must exist in the repo"
    )
