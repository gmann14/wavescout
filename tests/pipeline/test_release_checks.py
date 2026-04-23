from __future__ import annotations

import json
from pathlib import Path

from pipeline.scripts._release_checks import (
    build_release_readiness_report,
    extract_traceability_ids,
    has_report_or_takedown_path,
    missing_public_spot_detail_slugs,
    missing_release_blocking_traceability_ids,
)


def test_extract_traceability_ids_reads_all_release_blocking_rows() -> None:
    text = "| TR-01 | ... |\n| TR-02 | ... |\n| TR-20 | ... |"
    assert extract_traceability_ids(text) == {"TR-01", "TR-02", "TR-20"}


def test_missing_release_blocking_traceability_ids_flags_gaps() -> None:
    text = "| TR-01 | ... |\n| TR-02 | ... |"
    missing = missing_release_blocking_traceability_ids(text)
    assert "TR-03" in missing
    assert "TR-20" in missing


def test_has_report_or_takedown_path_detects_required_policy_language() -> None:
    assert has_report_or_takedown_path("The public product must support a simple report or takedown path.") is True
    assert has_report_or_takedown_path("No policy language here.") is False


def test_missing_public_spot_detail_slugs_only_checks_public_named(tmp_path: Path) -> None:
    spots_payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {
                    "slug": "lawrencetown-beach",
                    "publication_status": "public_named",
                }
            },
            {
                "properties": {
                    "slug": "candidate-a",
                    "publication_status": "public_coarse",
                }
            },
        ],
    }
    details_dir = tmp_path / "spots"
    details_dir.mkdir()

    assert missing_public_spot_detail_slugs(spots_payload, details_dir) == ["lawrencetown-beach"]

    (details_dir / "lawrencetown-beach.json").write_text("{}")
    assert missing_public_spot_detail_slugs(spots_payload, details_dir) == []


def test_build_release_readiness_report_marks_repo_ready_for_current_state() -> None:
    report = build_release_readiness_report()
    assert report["dataset"]["dataset_id"]
    assert report["checks"]["traceability"]["release_blocking_ids_present"] is True
    assert report["checks"]["policy"]["report_or_takedown_path_documented"] is True
    assert isinstance(report["failures"], list)
    assert report["ready"] is True
