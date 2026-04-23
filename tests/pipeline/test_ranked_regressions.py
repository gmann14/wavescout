from __future__ import annotations

import json
from pathlib import Path


RANKED_SEGMENTS_PATH = (
    Path(__file__).resolve().parents[2]
    / "pipeline"
    / "data"
    / "coastline"
    / "ns_ranked_segments.geojson"
)


def test_known_sheltered_false_positive_scores_below_open_coast_reference() -> None:
    payload = json.loads(RANKED_SEGMENTS_PATH.read_text())
    by_id = {feature["properties"]["segment_id"]: feature["properties"] for feature in payload["features"]}

    lahave_inner = by_id["ns-seg-01506"]
    broad_cove_outer = by_id["ns-seg-01268"]
    lawrencetown_open = by_id["ns-seg-03842"]

    assert lahave_inner["composite_score"] < 50.0
    assert broad_cove_outer["composite_score"] > lahave_inner["composite_score"]
    assert lawrencetown_open["composite_score"] > broad_cove_outer["composite_score"]


def test_geometry_only_open_coast_no_longer_ties_top_corroborated_leads() -> None:
    payload = json.loads(RANKED_SEGMENTS_PATH.read_text())
    by_id = {feature["properties"]["segment_id"]: feature["properties"] for feature in payload["features"]}

    geometry_only_open = by_id["ns-seg-01576"]
    corroborated_open = by_id["ns-seg-03842"]

    assert geometry_only_open["confidence"] == 1
    assert corroborated_open["confidence"] >= 2
    assert geometry_only_open["composite_score"] < corroborated_open["composite_score"]
