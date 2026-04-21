#!/usr/bin/env python3
"""Run release-readiness validation and emit a durable report."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _release_checks import build_release_readiness_report, write_release_readiness_report

ROOT = Path(__file__).resolve().parent.parent.parent
WEB_DIR = ROOT / "web"


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
        commands = [
            ([sys.executable, "pipeline/scripts/build_web_data.py"], ROOT),
            ([sys.executable, "pipeline/scripts/build_atlas_web_data.py"], ROOT),
            ([sys.executable, "pipeline/scripts/validate_public_dataset.py", "--strict", "--require-atlas"], ROOT),
            ([sys.executable, "-m", "pytest"], ROOT),
            (["pnpm", "test"], WEB_DIR),
            (["pnpm", "exec", "tsc", "--noEmit"], WEB_DIR),
            (["pnpm", "build"], WEB_DIR),
        ]
        if args.include_e2e:
            commands.append((["pnpm", "test:e2e"], WEB_DIR))

        for cmd, cwd in commands:
            result = run_command(cmd, cwd=cwd)
            command_results.append(result)
            if not result["ok"]:
                report = build_release_readiness_report(ROOT)
                report["command_results"] = command_results
                report["ready"] = False
                report["failures"] = report.get("failures", []) + [
                    f"Command failed: {result['command']}"
                ]
                out = write_release_readiness_report(report, args.report_out)
                print(f"Release readiness failed. Report written to {out}")
                return 1

    report = build_release_readiness_report(ROOT)
    report["command_results"] = command_results
    out = write_release_readiness_report(report, args.report_out)

    if not report["ready"]:
        print(f"Release readiness failed. Report written to {out}")
        for failure in report["failures"]:
            print(f"- {failure}")
        return 1

    print(f"Release readiness passed. Report written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
