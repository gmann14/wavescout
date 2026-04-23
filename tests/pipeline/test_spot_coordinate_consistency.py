from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPOTS_PATH = ROOT / "pipeline" / "data" / "ns_spots.geojson"
CONFIGS_DIR = ROOT / "pipeline" / "configs"


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * radius_m * math.asin(math.sqrt(a))


def test_public_spot_coordinates_do_not_wildly_drift_from_config_points() -> None:
    spots_payload = json.loads(SPOTS_PATH.read_text())
    spots_by_slug = {
        feature["properties"]["slug"]: feature
        for feature in spots_payload["features"]
        if feature["properties"].get("source") != "graham-local-knowledge"
    }

    checked = 0
    for path in CONFIGS_DIR.glob("*.json"):
        config = json.loads(path.read_text())
        slug = config.get("slug")
        point = config.get("point")
        if not slug or not point or slug not in spots_by_slug:
            continue

        feature = spots_by_slug[slug]
        lon, lat = feature["geometry"]["coordinates"]
        config_lon = float(point["lon"])
        config_lat = float(point["lat"])
        distance_m = haversine_m(lon, lat, config_lon, config_lat)

        assert distance_m <= 1200.0, (
            f"{slug} drifts {distance_m:.1f}m from pipeline config point; "
            "update ns_spots.geojson or the config so public spot coordinates stay aligned."
        )
        checked += 1

    assert checked >= 4
