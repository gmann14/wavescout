#!/usr/bin/env python3
"""Run release-readiness validation and emit a durable report.

The command surface is intentionally testable: ``build_command_plan``
returns a structured list of subprocess invocations that
``main`` then executes in order. Tests can call ``build_command_plan``
without spawning subprocesses, which keeps the documented release
gate easy to inspect from a clean checkout.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from _release_checks import (
        build_release_readiness_report,
        write_release_readiness_report,
    )
except ImportError:  # pragma: no cover - import path when used as pipeline.scripts.*
    from pipeline.scripts._release_checks import (
        build_release_readiness_report,
        write_release_readiness_report,
    )

ROOT = Path(__file__).resolve().parent.parent.parent
WEB_DIR = ROOT / "web"


def build_command_plan(
    *,
    python_executable: str | None = None,
    include_e2e: bool = False,
    repo_root: Path = ROOT,
    web_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Return the ordered subprocess plan for a full release-readiness run.

    ``python_executable`` defaults to ``sys.executable`` so the live
    command run uses the active interpreter, but tests can pass a
    deterministic value to assert plan shape without depending on the
    developer's local environment.
    """
    python = python_executable or sys.executable
    web = web_dir or (repo_root / "web")

    plan: list[tuple[list[str], Path]] = [
        ([python, "pipeline/scripts/build_web_data.py"], repo_root),
        ([python, "pipeline/scripts/build_atlas_web_data.py"], repo_root),
        (
            [
                python,
                "pipeline/scripts/validate_public_dataset.py",
                "--strict",
                "--require-atlas",
            ],
            repo_root,
        ),
        ([python, "-m", "pytest"], repo_root),
        (["pnpm", "test"], web),
        (["pnpm", "exec", "tsc", "--noEmit"], web),
        (["pnpm", "build"], web),
    ]
    if include_e2e:
        plan.append((["pnpm", "test:e2e"], web))

    return [
        {"cmd": cmd, "cwd": cwd, "command": " ".join(cmd)} for cmd, cwd in plan
    ]


def run_command(cmd: list[str], *, cwd: Path) -> dict[str, object]:
    """Run a subprocess and return a compact result summary."""
    completed = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    return {
        "command": " ".join(cmd),
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
        "ok": completed.returncode == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check WaveScout release readiness")
    parser.add_argument(
        "--include-e2e",
        action="store_true",
        help="Include Playwright browser checks in the release-readiness command run.",
    )
    parser.add_argument(
        "--skip-commands",
        action="store_true",
        help="Skip rebuild/test commands and only inspect current artifacts/docs.",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=None,
        help="Optional output path for the release-readiness report JSON.",
    )
    args = parser.parse_args()

    command_results: list[dict[str, object]] = []
    if not args.skip_commands:
        plan = build_command_plan(include_e2e=args.include_e2e)

        for entry in plan:
            result = run_command(entry["cmd"], cwd=entry["cwd"])
            command_results.append(result)
            if not result["ok"]:
                report = build_release_readiness_report(ROOT)
                report["command_results"] = command_results
                report["ready"] = False
                failure = f"Command failed: {result['command']}"
                report["failures"] = report.get("failures", []) + [failure]
                out = write_release_readiness_report(report, args.report_out)
                print(f"Release readiness failed. Report written to {out}")
                print(f"First failing command: {result['command']}")
                if result["stderr"]:
                    print("--- stderr (tail) ---")
                    print(result["stderr"])
                return 1

    report = build_release_readiness_report(ROOT)
    report["command_results"] = command_results

    out: Path | None = None
    if not args.skip_commands or args.report_out is not None:
        out = write_release_readiness_report(report, args.report_out)

    if not report["ready"]:
        if out is not None:
            print(f"Release readiness failed. Report written to {out}")
        else:
            print("Release readiness failed. No report written in --skip-commands mode.")
        for failure in report["failures"]:
            print(f"- {failure}")
        return 1

    if out is not None:
        print(f"Release readiness passed. Report written to {out}")
    else:
        print("Release readiness passed. No report written in --skip-commands mode.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
