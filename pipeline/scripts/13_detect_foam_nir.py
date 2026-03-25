#!/usr/bin/env python3
"""Phase 2.5, Script 13: Automated NIR foam detection per coastline segment.

For a given spot config, loads coastline segments within the spot's bbox,
then for each clear Sentinel-2 scene (post-2021-10, <15% cloud), extracts
NIR (B8) values in a nearshore buffer zone (0-200m seaward of the coastline).

Computes per-segment per-scene foam metrics:
  - foam_fraction: pixels above NIR threshold / total water pixels in buffer
  - foam_extent_m: estimated linear meters of foam along the segment
  - mean_nir: average NIR in buffer
  - max_nir: peak NIR in buffer

Pairs each observation with marine conditions from Open-Meteo.

Output: pipeline/data/manifests/<slug>_foam_detections.json

Usage:
    python3 pipeline/scripts/13_detect_foam_nir.py
    python3 pipeline/scripts/13_detect_foam_nir.py --config pipeline/configs/cow-bay.json
    python3 pipeline/scripts/13_detect_foam_nir.py --limit 10  # test with 10 scenes
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from _script_utils import (
    DEFAULT_CONFIG_PATH,
    default_manifest_path,
    generate_run_id,
    get_code_version,
    init_gee,
    load_region_config,
    now_utc_iso,
    write_json,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEGMENTS_PATH = Path(__file__).resolve().parents[1] / "data" / "coastline" / "ns_segments.geojson"

# NIR threshold for foam detection (B8 reflectance in SR units)
# Water is typically 50-200, foam/whitecap is 800-3000+
NIR_FOAM_THRESHOLD = 800

# Buffer distance from coastline into the water (meters)
BUFFER_DISTANCE_M = 200

# Sentinel-2 pixel size
PIXEL_SIZE_M = 10

# Cloud cover filter for scene selection
MAX_CLOUD_PERCENT = 15.0

# Open-Meteo marine swell data available from ~2021-10 onward at this location.
# Earlier scenes still produce foam metrics but will have null conditions.
MIN_DATE = "2021-10-01"

# GEE rate limit: pause between scene queries (seconds)
GEE_PAUSE_S = 0.3

# Open-Meteo rate limit: pause between API calls (seconds)
METEO_PAUSE_S = 0.25


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_segments_in_bbox(bbox: list[float]) -> list[dict]:
    """Load coastline segments whose centroid falls within the spot's bbox.

    Args:
        bbox: [west, south, east, north] from the spot config.

    Returns:
        List of GeoJSON features.
    """
    if not SEGMENTS_PATH.exists():
        print(f"ERROR: {SEGMENTS_PATH} not found. Run 10_segment_coastline.py first.")
        sys.exit(1)

    with SEGMENTS_PATH.open() as f:
        data = json.load(f)

    west, south, east, north = bbox
    segments = []
    for feat in data["features"]:
        props = feat["properties"]
        lat, lon = props["centroid_lat"], props["centroid_lon"]
        if south <= lat <= north and west <= lon <= east:
            segments.append(feat)

    return segments


def build_seaward_buffer(segment_coords: list[list[float]], orientation_deg: float) -> dict | None:
    """Build a GEE-compatible polygon buffer on the seaward side of a segment.

    Creates a buffer by offsetting the segment line toward the ocean
    (along the seaward normal direction).

    Args:
        segment_coords: [[lon, lat], ...] from the GeoJSON geometry.
        orientation_deg: Seaward-facing normal bearing in degrees.

    Returns:
        ee.Geometry.Polygon dict or None if degenerate.
    """
    import ee

    # Build the segment as an ee.Geometry.LineString
    line = ee.Geometry.LineString(segment_coords)

    # Buffer the full line by BUFFER_DISTANCE_M (creates a polygon around the line)
    full_buffer = line.buffer(BUFFER_DISTANCE_M)

    # To get only the seaward side, we create a "land mask" by buffering a line
    # offset landward by a small amount. The seaward buffer = full_buffer - land_side.
    #
    # Approach: offset each coordinate landward (opposite of orientation_deg),
    # create a polygon on the land side, then subtract from the full buffer.
    #
    # The landward direction is orientation_deg + 180 degrees.
    landward_deg = (orientation_deg + 180) % 360
    landward_rad = math.radians(landward_deg)

    # Offset distance in degrees (approximate: 1 degree ~ 111km at equator,
    # but we need meters. At lat 44.6, 1 deg lon ~ 79km, 1 deg lat ~ 111km)
    # Use a generous offset to clip the land side.
    offset_lat = (BUFFER_DISTANCE_M / 111000) * math.cos(landward_rad)
    offset_lon = (BUFFER_DISTANCE_M / (111000 * math.cos(math.radians(44.6)))) * math.sin(landward_rad)

    landward_coords = [[lon + offset_lon, lat + offset_lat] for lon, lat in segment_coords]
    landward_line = ee.Geometry.LineString(landward_coords)
    landward_buffer = landward_line.buffer(BUFFER_DISTANCE_M * 0.5)

    # Seaward buffer = full buffer minus the landward area
    seaward_buffer = full_buffer.difference(landward_buffer)

    return seaward_buffer


def get_clear_scene_dates(bbox: list[float], max_cloud: float, min_date: str) -> list[str]:
    """Query GEE for clear Sentinel-2 scene dates within the bbox.

    Returns sorted list of date strings (YYYY-MM-DD), filtered to post-min_date
    and below max_cloud threshold.
    """
    import ee

    roi = ee.Geometry.Rectangle(bbox)
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(min_date, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
    )

    dates = (
        collection.aggregate_array("system:time_start")
        .map(lambda t: ee.Date(t).format("YYYY-MM-dd"))
        .distinct()
        .sort()
        .getInfo()
    )

    return dates


def extract_foam_metrics(
    date: str, segment_buffer: object, bbox: list[float]
) -> dict | None:
    """Extract NIR foam metrics for a single scene + segment buffer.

    Uses GEE server-side computation (reduceRegion) to avoid downloading imagery.

    Returns dict with foam metrics or None on error.
    """
    import ee

    roi = ee.Geometry.Rectangle(bbox)

    # Get the Sentinel-2 image for this date
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(date, ee.Date(date).advance(1, "day"))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PERCENT))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )

    count = collection.size().getInfo()
    if count == 0:
        return None

    image = collection.first()

    # Extract NIR band (B8) and SCL (Scene Classification Layer)
    nir = image.select("B8")
    scl = image.select("SCL")

    # Mask to water pixels only using SCL:
    # SCL 6 = water. Also allow SCL 3 (cloud shadow on water) as it may contain foam.
    water_mask = scl.eq(6).Or(scl.eq(3))

    # Apply water mask to NIR
    nir_water = nir.updateMask(water_mask)

    # Compute foam mask: NIR > threshold
    foam_mask = nir_water.gt(NIR_FOAM_THRESHOLD)

    # Reduce over the segment buffer
    stats = nir_water.reduceRegion(
        reducer=ee.Reducer.mean()
        .combine(ee.Reducer.max(), sharedInputs=True)
        .combine(ee.Reducer.count(), sharedInputs=True),
        geometry=segment_buffer,
        scale=PIXEL_SIZE_M,
        maxPixels=1e6,
    ).getInfo()

    foam_stats = foam_mask.reduceRegion(
        reducer=ee.Reducer.sum().combine(ee.Reducer.count(), sharedInputs=True),
        geometry=segment_buffer,
        scale=PIXEL_SIZE_M,
        maxPixels=1e6,
    ).getInfo()

    # Parse results
    mean_nir = stats.get("B8_mean")
    max_nir = stats.get("B8_max")
    water_pixel_count = stats.get("B8_count")
    foam_pixel_count = foam_stats.get("B8_sum")  # sum of binary mask = count of True
    total_in_buffer = foam_stats.get("B8_count")

    if water_pixel_count is None or water_pixel_count == 0:
        return None

    foam_fraction = (foam_pixel_count or 0) / water_pixel_count
    # Estimate linear foam extent: foam pixels * pixel_size / buffer_width * segment_length
    # Simplified: foam_pixels * pixel_area / buffer_distance gives a rough "foam width"
    # But we want linear meters along the segment, so:
    # foam_extent_m ≈ foam_pixel_count * PIXEL_SIZE_M^2 / BUFFER_DISTANCE_M
    foam_extent_m = (foam_pixel_count or 0) * (PIXEL_SIZE_M ** 2) / BUFFER_DISTANCE_M

    return {
        "foam_fraction": round(foam_fraction, 4),
        "foam_extent_m": round(foam_extent_m, 1),
        "mean_nir": round(mean_nir, 1) if mean_nir is not None else None,
        "max_nir": round(max_nir, 1) if max_nir is not None else None,
        "water_pixel_count": water_pixel_count,
        "foam_pixel_count": foam_pixel_count or 0,
        "total_buffer_pixels": total_in_buffer,
    }


def get_marine_conditions_for_date(lat: float, lon: float, date: str) -> dict:
    """Fetch marine conditions from Open-Meteo for a specific date at ~11 UTC.

    Returns dict with swell_height_m, swell_period_s, swell_direction_deg.
    """
    import requests

    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date,
        "end_date": date,
        "hourly": "swell_wave_height,swell_wave_period,swell_wave_direction,wave_height",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {
            "swell_height_m": None,
            "swell_period_s": None,
            "swell_direction_deg": None,
            "wave_height_m": None,
        }

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return {
            "swell_height_m": None,
            "swell_period_s": None,
            "swell_direction_deg": None,
            "wave_height_m": None,
        }

    # Sentinel-2 overpass at ~11 UTC
    idx = min(11, len(times) - 1)

    return {
        "swell_height_m": hourly.get("swell_wave_height", [None])[idx],
        "swell_period_s": hourly.get("swell_wave_period", [None])[idx],
        "swell_direction_deg": hourly.get("swell_wave_direction", [None])[idx],
        "wave_height_m": hourly.get("wave_height", [None])[idx],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NIR foam detection per coastline segment across Sentinel-2 archive."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to spot config JSON. Default: {DEFAULT_CONFIG_PATH}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Max number of scenes to process (for testing). Default: all.",
    )
    parser.add_argument(
        "--nir-threshold",
        type=int,
        default=NIR_FOAM_THRESHOLD,
        help=f"NIR threshold for foam detection. Default: {NIR_FOAM_THRESHOLD}",
    )
    parser.add_argument(
        "--buffer-m",
        type=int,
        default=BUFFER_DISTANCE_M,
        help=f"Nearshore buffer distance in meters. Default: {BUFFER_DISTANCE_M}",
    )
    parser.add_argument(
        "--skip-conditions",
        action="store_true",
        help="Skip Open-Meteo conditions lookup (faster for testing).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Override output path.",
    )
    parser.add_argument(
        "--project",
        help="GEE cloud project ID. Default: GEE_PROJECT env var.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    global NIR_FOAM_THRESHOLD, BUFFER_DISTANCE_M
    NIR_FOAM_THRESHOLD = args.nir_threshold
    BUFFER_DISTANCE_M = args.buffer_m

    print("=" * 60)
    print("Phase 2.5: NIR Foam Detection")
    print("=" * 60)

    config = load_region_config(args.config)
    slug = config["slug"]
    bbox = config["bbox"]
    point = config.get("point", {})
    lat = point.get("lat")
    lon = point.get("lon")

    print(f"Spot: {config['name']} ({slug})")
    print(f"Bbox: {bbox}")
    print(f"NIR threshold: {NIR_FOAM_THRESHOLD}")
    print(f"Buffer distance: {BUFFER_DISTANCE_M}m")

    # Load segments within the spot's bbox
    segments = load_segments_in_bbox(bbox)
    print(f"Segments in bbox: {len(segments)}")

    if not segments:
        print("ERROR: No segments found in bbox. Check your config bbox against ns_segments.geojson.")
        sys.exit(1)

    # Initialize GEE
    print("\nInitializing Google Earth Engine...")
    init_gee(args.project)
    import ee

    # Get clear scene dates
    print(f"Querying clear scenes (post-{MIN_DATE}, <{MAX_CLOUD_PERCENT}% cloud)...")
    scene_dates = get_clear_scene_dates(bbox, MAX_CLOUD_PERCENT, MIN_DATE)
    print(f"Clear scenes available: {len(scene_dates)}")

    if args.limit:
        scene_dates = scene_dates[: args.limit]
        print(f"Limited to first {args.limit} scenes")

    if not scene_dates:
        print("ERROR: No clear scenes found. Check GEE access and date range.")
        sys.exit(1)

    # Pre-build seaward buffers for each segment (reused across all scenes)
    print("\nBuilding seaward buffers for each segment...")
    segment_buffers: list[tuple[dict, object]] = []
    for feat in segments:
        props = feat["properties"]
        coords = feat["geometry"]["coordinates"]
        orientation = props["orientation_deg"]
        buffer_geom = build_seaward_buffer(coords, orientation)
        if buffer_geom is not None:
            segment_buffers.append((feat, buffer_geom))

    print(f"Valid segment buffers: {len(segment_buffers)}")

    # Process each scene x segment combination
    total_combos = len(scene_dates) * len(segment_buffers)
    print(f"\nProcessing {len(scene_dates)} scenes x {len(segment_buffers)} segments = {total_combos} combinations")
    print("-" * 60)

    detections: list[dict] = []
    conditions_cache: dict[str, dict] = {}
    errors = 0

    for i, date in enumerate(scene_dates):
        # Fetch conditions for this date (once per date, shared across segments)
        if not args.skip_conditions and date not in conditions_cache:
            conditions_cache[date] = get_marine_conditions_for_date(lat, lon, date)
            time.sleep(METEO_PAUSE_S)

        conditions = conditions_cache.get(date, {})
        swell_h = conditions.get("swell_height_m")
        swell_p = conditions.get("swell_period_s")
        swell_d = conditions.get("swell_direction_deg")

        swell_str = f"{swell_h}m" if swell_h is not None else "N/A"
        print(f"[{i + 1}/{len(scene_dates)}] {date} (swell: {swell_str})")

        for j, (feat, buffer_geom) in enumerate(segment_buffers):
            seg_id = feat["properties"]["segment_id"]

            try:
                metrics = extract_foam_metrics(date, buffer_geom, bbox)
            except Exception as exc:
                print(f"  ERROR {seg_id}: {exc}")
                errors += 1
                continue

            if metrics is None:
                continue

            detection = {
                "segment_id": seg_id,
                "date": date,
                "swell_height_m": swell_h,
                "swell_period_s": swell_p,
                "swell_direction_deg": swell_d,
                "wave_height_m": conditions.get("wave_height_m"),
                **metrics,
            }
            detections.append(detection)

            foam_str = f"foam={metrics['foam_fraction']:.3f}"
            nir_str = f"mean_nir={metrics['mean_nir']}"
            print(f"  {seg_id}: {foam_str}, {nir_str}, pixels={metrics['water_pixel_count']}")

            time.sleep(GEE_PAUSE_S)

    # Write output
    run_id = generate_run_id()
    output_path = args.output or default_manifest_path("foam_detections", slug)

    payload = {
        "script": "13_detect_foam_nir.py",
        "run_id": run_id,
        "generated_at_utc": now_utc_iso(),
        "code_version": get_code_version(),
        "config": {
            "spot": config["name"],
            "slug": slug,
            "bbox": bbox,
            "point": {"lat": lat, "lon": lon},
        },
        "parameters": {
            "nir_foam_threshold": NIR_FOAM_THRESHOLD,
            "buffer_distance_m": BUFFER_DISTANCE_M,
            "pixel_size_m": PIXEL_SIZE_M,
            "max_cloud_percent": MAX_CLOUD_PERCENT,
            "min_date": MIN_DATE,
        },
        "summary": {
            "scenes_processed": len(scene_dates),
            "segments_processed": len(segment_buffers),
            "total_detections": len(detections),
            "errors": errors,
            "scenes_with_foam": len({d["date"] for d in detections if d["foam_fraction"] > 0.05}),
            "date_range": {
                "start": scene_dates[0] if scene_dates else None,
                "end": scene_dates[-1] if scene_dates else None,
            },
        },
        "detections": detections,
    }

    write_json(output_path, payload)

    print(f"\n{'=' * 60}")
    print(f"RESULTS")
    print(f"{'=' * 60}")
    print(f"Scenes processed: {len(scene_dates)}")
    print(f"Segments processed: {len(segment_buffers)}")
    print(f"Total detections: {len(detections)}")
    print(f"Errors: {errors}")

    if detections:
        foam_fracs = [d["foam_fraction"] for d in detections]
        print(f"\nFoam fraction stats:")
        print(f"  Min:  {min(foam_fracs):.4f}")
        print(f"  Max:  {max(foam_fracs):.4f}")
        print(f"  Mean: {sum(foam_fracs) / len(foam_fracs):.4f}")

        foamy = [d for d in detections if d["foam_fraction"] > 0.05]
        print(f"\nDetections with foam_fraction > 0.05: {len(foamy)}")

    print(f"\nManifest saved to {output_path}")


if __name__ == "__main__":
    main()
