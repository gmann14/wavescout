#!/usr/bin/env python3
"""Promote the current public dataset after a successful release-readiness check."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _release_checks import write_promoted_dataset_record

ROOT = Path(__file__).resolve().parent.parent.parent
WEB_DATA = ROOT / "web" / "public" / "data"
MANIFESTS = ROOT / "pipeline" / "data" / "manifests"


def _read_json(path: Path) -> dict:
    with path.open() as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote the current WaveScout public dataset")
    parser.add_argument("--release-reviewer", required=True, help="Name of the release reviewer")
    parser.add_argument("--policy-reviewer", required=True, help="Name of the policy reviewer")
    parser.add_argument("--review-record", required=True, help="Durable location of the Gate D review record")
    parser.add_argument(
        "--gate-outcome",
        required=True,
        choices=("pass", "pass_with_follow_ups"),
        help="Gate D outcome required for promotion",
    )
    args = parser.parse_args()

    readiness_path = MANIFESTS / "release_readiness_report.json"
    if not readiness_path.exists():
        raise SystemExit("Release readiness report missing. Run check_release_readiness.py first.")

    readiness = _read_json(readiness_path)
    if not readiness.get("ready"):
        raise SystemExit("Release readiness report is not green. Promotion aborted.")

    manifest_path = WEB_DATA / "dataset-manifest.json"
    manifest = _read_json(manifest_path)
    manifest["status"] = "promoted"
    with manifest_path.open("w") as handle:
        json.dump(manifest, handle, separators=(",", ":"))

    record_path = write_promoted_dataset_record(
        dataset_manifest_path=manifest_path,
        release_review=args.release_reviewer,
        policy_review=args.policy_reviewer,
        review_record=args.review_record,
        gate_outcome=args.gate_outcome,
    )
    print(f"Dataset promoted. Record written to {record_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
