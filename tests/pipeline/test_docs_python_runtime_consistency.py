"""Ensure docs name the same supported Python runtime for release checks.

This stops a future docs update from silently disagreeing with
``requirements.txt`` and the README setup instructions.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOC_PATHS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "CODEX-CLOUD-SETUP.md",
    REPO_ROOT / "docs" / "RELEASE-CHECKLIST.md",
)
RUNTIME_PATTERN = re.compile(r"python3\.(\d+)")
RELEASE_CONTEXT_PATTERN = re.compile(
    r"(check_release_readiness|promote_public_dataset|build_web_data|build_atlas_web_data|python3\.\d+ -m venv)"
)


def test_docs_reference_same_python_minor_version() -> None:
    matches: dict[Path, set[str]] = {}
    for path in DOC_PATHS:
        lines = [
            line for line in path.read_text().splitlines()
            if RELEASE_CONTEXT_PATTERN.search(line)
        ]
        text = "\n".join(lines)
        found = set(RUNTIME_PATTERN.findall(text))
        if found:
            matches[path] = found

    assert matches, (
        "expected at least one doc to name an explicit python3.X runtime for release checks"
    )

    all_versions = set().union(*matches.values())
    assert len(all_versions) == 1, (
        "docs disagree on the supported Python runtime: "
        + ", ".join(f"{p.name}={sorted(v)}" for p, v in matches.items())
    )
