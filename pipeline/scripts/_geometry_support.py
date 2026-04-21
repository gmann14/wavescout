from __future__ import annotations

import json
from pathlib import Path


def load_legacy_road_scores(path: Path) -> dict[str, float]:
    """Reuse prior road-access scores when road geometry cache is unavailable."""
    if not path.exists():
        return {}

    with path.open() as f:
        data = json.load(f)

    scores: dict[str, float] = {}
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        seg_id = props.get("segment_id")
        road_score = props.get("road_access_score")
        if seg_id and isinstance(road_score, (int, float)):
            scores[seg_id] = float(road_score)
    return scores
