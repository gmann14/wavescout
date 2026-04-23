#!/usr/bin/env python3
"""Helpers for release-readiness validation and promotion records."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
WEB_DATA = ROOT / "web" / "public" / "data"
MANIFESTS = ROOT / "pipeline" / "data" / "manifests"
TRACEABILITY_DOC = ROOT / "docs" / "TRACEABILITY.md"
PUBLIC_OUTPUT_POLICY_DOC = ROOT / "docs" / "PUBLIC-OUTPUT-POLICY.md"
DOC_SYNC_PATHS = [
    ROOT / "README.md",
    ROOT / "docs" / "SPEC.md",
    ROOT / "docs" / "DATA-CONTRACTS.md",
    ROOT / "docs" / "UI-STATES.md",
    ROOT / "docs" / "REVIEW-GATES.md",
    ROOT / "DEPLOY.md",
]
RELEASE_BLOCKING_TRACEABILITY_IDS = tuple(f"TR-{index:02d}" for index in range(1, 21))
TRACEABILITY_ID_PATTERN = re.compile(r"\bTR-\d{2}\b")
TAKEDOWN_POLICY_PATTERN = re.compile(r"report or takedown path", re.IGNORECASE)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def extract_traceability_ids(text: str) -> set[str]:
    """Extract traceability IDs from the traceability markdown doc."""
    return set(TRACEABILITY_ID_PATTERN.findall(text))


def missing_release_blocking_traceability_ids(text: str) -> list[str]:
    """Return any missing release-blocking traceability IDs."""
    present = extract_traceability_ids(text)
    return [trace_id for trace_id in RELEASE_BLOCKING_TRACEABILITY_IDS if trace_id not in present]


def has_report_or_takedown_path(policy_text: str) -> bool:
    """Return whether the policy doc explicitly includes the required path."""
    return TAKEDOWN_POLICY_PATTERN.search(policy_text) is not None


def missing_public_spot_detail_slugs(spots_payload: dict[str, Any], spot_details_dir: Path) -> list[str]:
    """Return public named spot slugs missing a detail payload."""
    missing: list[str] = []
    for feature in spots_payload.get("features", []):
        props = feature.get("properties", {})
        if props.get("publication_status") != "public_named":
            continue
        slug = props.get("slug")
        if not slug:
            continue
        if not (spot_details_dir / f"{slug}.json").exists():
            missing.append(slug)
    return sorted(missing)


def build_release_readiness_report(root: Path = ROOT) -> dict[str, Any]:
    """Build a machine-readable release-readiness report from current artifacts."""
    web_data = root / "web" / "public" / "data"
    manifest_path = web_data / "dataset-manifest.json"
    manifest = _read_json(manifest_path)
    spots_payload = _read_json(web_data / "spots.json")
    gallery_payload = _read_json(web_data / "gallery.json")
    traceability_text = (root / "docs" / "TRACEABILITY.md").read_text()
    policy_text = (root / "docs" / "PUBLIC-OUTPUT-POLICY.md").read_text()

    artifact_checks = {
        "dataset_manifest_exists": manifest_path.exists(),
        "spots_exists": (web_data / "spots.json").exists(),
        "segments_high_exists": (web_data / "segments-high.json").exists(),
        "segments_all_exists": (web_data / "segments-all.json").exists(),
        "gallery_exists": (web_data / "gallery.json").exists(),
        "atlas_sections_exists": (web_data / "atlas" / "sections.json").exists(),
        "atlas_gallery_exists": (web_data / "atlas" / "gallery.json").exists(),
    }

    provenance_checks = {
        "dataset_manifest_has_run_id": bool(manifest.get("run_id")),
        "dataset_manifest_has_generated_at": bool(manifest.get("generated_at_utc")),
        "dataset_manifest_has_code_version": bool(manifest.get("code_version")),
        "dataset_manifest_has_config_version": bool(manifest.get("config_version")),
        "gallery_has_run_id": bool(gallery_payload.get("run_id")),
        "gallery_has_generated_at": bool(gallery_payload.get("generated_at_utc")),
        "gallery_has_code_version": bool(gallery_payload.get("code_version")),
    }

    missing_details = missing_public_spot_detail_slugs(spots_payload, web_data / "spots")
    traceability_missing = missing_release_blocking_traceability_ids(traceability_text)
    docs_sync = {str(path.relative_to(root)): path.exists() for path in DOC_SYNC_PATHS}

    checks = {
        "artifacts": artifact_checks,
        "provenance": provenance_checks,
        "spot_details": {
            "missing_public_named_spot_details": missing_details,
            "all_public_named_spot_details_present": not missing_details,
        },
        "traceability": {
            "missing_release_blocking_ids": traceability_missing,
            "release_blocking_ids_present": not traceability_missing,
        },
        "policy": {
            "report_or_takedown_path_documented": has_report_or_takedown_path(policy_text),
        },
        "docs_sync": docs_sync,
    }

    failures: list[str] = []
    for section, values in checks.items():
        if section == "spot_details":
            if values["missing_public_named_spot_details"]:
                failures.append(
                    "Missing public named spot detail payloads: "
                    + ", ".join(values["missing_public_named_spot_details"])
                )
            continue
        if section == "traceability":
            if values["missing_release_blocking_ids"]:
                failures.append(
                    "Missing release-blocking traceability IDs: "
                    + ", ".join(values["missing_release_blocking_ids"])
                )
            continue
        for key, value in values.items():
            if value is not True:
                failures.append(f"{section}.{key} failed")

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "dataset": {
            "dataset_id": manifest.get("dataset_id"),
            "status": manifest.get("status"),
            "run_id": manifest.get("run_id"),
            "code_version": manifest.get("code_version"),
        },
        "checks": checks,
        "ready": not failures,
        "failures": failures,
    }


def write_release_readiness_report(report: dict[str, Any], out_path: Path | None = None) -> Path:
    """Persist a release-readiness report to disk."""
    target = out_path or (MANIFESTS / "release_readiness_report.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w") as handle:
        json.dump(report, handle, indent=2)
    return target


def write_promoted_dataset_record(
    *,
    dataset_manifest_path: Path,
    release_review: str,
    policy_review: str,
    review_record: str,
    gate_outcome: str,
    out_path: Path | None = None,
) -> Path:
    """Write a durable promoted-dataset record for Gate D."""
    manifest = _read_json(dataset_manifest_path)
    target = out_path or (MANIFESTS / "promoted_dataset_record.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "dataset_id": manifest.get("dataset_id"),
        "run_id": manifest.get("run_id"),
        "code_version": manifest.get("code_version"),
        "status": manifest.get("status"),
        "release_reviewer": release_review,
        "policy_reviewer": policy_review,
        "review_record": review_record,
        "gate_outcome": gate_outcome,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
    }
    with target.open("w") as handle:
        json.dump(record, handle, indent=2)
    return target
