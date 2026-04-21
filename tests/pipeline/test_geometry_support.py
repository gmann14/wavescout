from __future__ import annotations

import json
from pathlib import Path

from pipeline.scripts._geometry_support import load_legacy_road_scores


def test_load_legacy_road_scores_reads_existing_scores(tmp_path: Path) -> None:
    path = tmp_path / "ns_scored_segments.geojson"
    payload = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"segment_id": "a", "road_access_score": 15.0}},
            {"type": "Feature", "properties": {"segment_id": "b", "road_access_score": 7.5}},
            {"type": "Feature", "properties": {"segment_id": "c"}},
        ],
    }
    path.write_text(json.dumps(payload))

    assert load_legacy_road_scores(path) == {"a": 15.0, "b": 7.5}


def test_load_legacy_road_scores_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert load_legacy_road_scores(tmp_path / "missing.geojson") == {}
