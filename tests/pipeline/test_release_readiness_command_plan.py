"""Tests for the release-readiness command plan builder.

These tests pin the documented command surface of
``pipeline/scripts/check_release_readiness.py`` so the plan can be
inspected without actually executing the subprocesses.
"""
from __future__ import annotations

from pathlib import Path
import sys

from pipeline.scripts import check_release_readiness as module


def _commands(plan):
    """Return the list of command strings from a plan."""
    return [entry["command"] for entry in plan]


def test_build_command_plan_includes_required_commands() -> None:
    plan = module.build_command_plan(python_executable="python3.12")
    cmds = _commands(plan)

    assert cmds == [
        "python3.12 pipeline/scripts/build_web_data.py",
        "python3.12 pipeline/scripts/build_atlas_web_data.py",
        "python3.12 pipeline/scripts/validate_public_dataset.py --strict --require-atlas",
        "python3.12 -m pytest",
        "pnpm test",
        "pnpm exec tsc --noEmit",
        "pnpm build",
    ]


def test_build_command_plan_include_e2e_appends_browser_command() -> None:
    plan = module.build_command_plan(
        python_executable="python3.12", include_e2e=True
    )
    cmds = _commands(plan)
    assert cmds[-1] == "pnpm test:e2e"


def test_build_command_plan_uses_injectable_python_executable() -> None:
    plan = module.build_command_plan(python_executable="/custom/python")
    python_cmds = [
        entry for entry in plan if entry["cmd"][0] == "/custom/python"
    ]
    assert python_cmds, "expected Python commands to use the injected interpreter"
    # No entry should hardcode a non-injected interpreter
    other_python = [
        entry
        for entry in plan
        if entry["cmd"][0] not in {"/custom/python", "pnpm"}
    ]
    assert not other_python, f"unexpected interpreters in plan: {other_python}"


def test_build_command_plan_uses_repo_root_cwd() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    web_dir = repo_root / "web"
    plan = module.build_command_plan(python_executable="python3.12")
    for entry in plan:
        if entry["cmd"][0] == "pnpm":
            assert entry["cwd"] == web_dir
        else:
            assert entry["cwd"] == repo_root


def test_build_command_plan_emits_dicts_with_required_fields() -> None:
    plan = module.build_command_plan(python_executable="python3.12")
    for entry in plan:
        assert isinstance(entry, dict)
        assert "cmd" in entry and isinstance(entry["cmd"], list)
        assert "cwd" in entry and isinstance(entry["cwd"], Path)
        assert "command" in entry and isinstance(entry["command"], str)


def test_skip_commands_does_not_rewrite_default_report(monkeypatch) -> None:
    monkeypatch.setattr(
        module,
        "build_release_readiness_report",
        lambda root: {"ready": True, "failures": []},
    )

    def fail_write(*args, **kwargs):
        raise AssertionError("--skip-commands should not write the default report")

    monkeypatch.setattr(module, "write_release_readiness_report", fail_write)
    monkeypatch.setattr(
        sys, "argv", ["check_release_readiness.py", "--skip-commands"]
    )

    assert module.main() == 0
