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

Also computes per-scene SCL quality metrics:
  - cloud_pct: % of AOI pixels classified as cloud (SCL 8, 9, 10)
  - shadow_pct: % of AOI pixels classified as cloud shadow (SCL 3)
  - snow_land_pct: % of non-water AOI pixels classified as snow (SCL 11)
  - valid_pct: % of AOI pixels with actual data (non-nodata)
  - quality_score: composite 0-100 (cloud 40%, valid 30%, snow 20%, shadow 10%)

Pairs each observation with marine conditions from Open-Meteo.

Output: pipeline/data/manifests/<slug>_foam_detections.json

Usage:
    python3 pipeline/scripts/13_detect_foam_nir.py
    python3 pipeline/scripts/13_detect_foam_nir.py --config pipeline/configs/cow-bay.json
    python3 pipeline/scripts/13_detect_foam_nir.py --limit 10  # test with 10 scenes
    python3 pipeline/scripts/13_detect_foam_nir.py --all-spots  # process all configs
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

# SCL class constants
SCL_NO_DATA = 0
SCL_CLOUD_SHADOW = 3
SCL_WATER = 6
SCL_CLOUD_MEDIUM = 8
SCL_CLOUD_HIGH = 9
SCL_THIN_CIRRUS = 10
SCL_SNOW_ICE = 11

# Quality score minimum thresholds
QUALITY_DISCARD_THRESHOLD = 40   # < 40 → discard from statistics
QUALITY_USABLE_THRESHOLD = 60    # >= 60 → usable for analysis
QUALITY_HIGH_THRESHOLD = 80      # >= 80 → high quality (preferred for gallery)


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


def get_scl_quality_metrics(date: str, bbox: list[float]) -> dict:
    """Compute SCL-based scene quality metrics for a single date over the AOI.

    Calculates:
      - cloud_pct: % of AOI pixels classified as cloud (SCL 8, 9, 10)
      - shadow_pct: % of AOI pixels classified as cloud shadow (SCL 3)
      - snow_land_pct: % of non-water AOI pixels classified as snow (SCL 11)
      - valid_pct: % of pixels with actual data (SCL != 0)
      - quality_score: composite 0-100

    Quality score weighting:
      cloud 40% + valid 30% + snow 20% + shadow 10%

    Args:
        date: YYYY-MM-DD string.
        bbox: [west, south, east, north] bounding box.

    Returns:
        Dict with quality metrics. Returns degraded defaults on error.
    """
    import ee

    default_metrics = {
        "cloud_pct": None,
        "shadow_pct": None,
        "snow_land_pct": None,
        "valid_pct": None,
        "quality_score": None,
    }

    try:
        roi = ee.Geometry.Rectangle(bbox)

        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(roi)
            .filterDate(date, ee.Date(date).advance(1, "day"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PERCENT))
            .sort("CLOUDY_PIXEL_PERCENTAGE")
        )

        count = collection.size().getInfo()
        if count == 0:
            return default_metrics

        image = collection.first()
        scl = image.select("SCL")

        # Total pixel count in AOI (includes nodata=0)
        total_stats = scl.gte(0).reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=roi,
            scale=PIXEL_SIZE_M,
            maxPixels=1e8,
        ).getInfo()
        total_pixels = total_stats.get("SCL", 0)

        if not total_pixels:
            return default_metrics

        # Valid pixels: SCL != 0 (not nodata/swath edge)
        valid_mask = scl.neq(SCL_NO_DATA)
        valid_stats = valid_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=PIXEL_SIZE_M,
            maxPixels=1e8,
        ).getInfo()
        valid_pixels = valid_stats.get("SCL", 0)
        valid_pct = (valid_pixels / total_pixels) * 100 if total_pixels else 0

        # Cloud pixels: SCL 8, 9, 10 (medium cloud, high cloud, thin cirrus)
        cloud_mask = scl.eq(SCL_CLOUD_MEDIUM).Or(scl.eq(SCL_CLOUD_HIGH)).Or(scl.eq(SCL_THIN_CIRRUS))
        cloud_stats = cloud_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=PIXEL_SIZE_M,
            maxPixels=1e8,
        ).getInfo()
        cloud_pixels = cloud_stats.get("SCL", 0)
        cloud_pct = (cloud_pixels / total_pixels) * 100 if total_pixels else 0

        # Shadow pixels: SCL 3 (cloud shadow)
        shadow_mask = scl.eq(SCL_CLOUD_SHADOW)
        shadow_stats = shadow_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=PIXEL_SIZE_M,
            maxPixels=1e8,
        ).getInfo()
        shadow_pixels = shadow_stats.get("SCL", 0)
        shadow_pct = (shadow_pixels / total_pixels) * 100 if total_pixels else 0

        # Snow on land: SCL 11 pixels that are NOT water (SCL 6)
        # i.e., snow-classified pixels outside water areas
        snow_land_mask = scl.eq(SCL_SNOW_ICE).And(scl.neq(SCL_WATER))
        non_water_mask = scl.neq(SCL_WATER).And(scl.neq(SCL_NO_DATA))

        snow_land_stats = snow_land_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=PIXEL_SIZE_M,
            maxPixels=1e8,
        ).getInfo()
        non_water_stats = non_water_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=PIXEL_SIZE_M,
            maxPixels=1e8,
        ).getInfo()

        snow_land_pixels = snow_land_stats.get("SCL", 0)
        non_water_pixels = non_water_stats.get("SCL", 1)  # avoid div-by-zero
        snow_land_pct = (snow_land_pixels / non_water_pixels) * 100 if non_water_pixels else 0

        # Composite quality score (0-100)
        # Higher is better. Each component contributes its max weight when clean.
        cloud_score = (1.0 - min(cloud_pct / 100.0, 1.0)) * 40.0
        valid_score = min(valid_pct / 100.0, 1.0) * 30.0
        snow_score = (1.0 - min(snow_land_pct / 100.0, 1.0)) * 20.0
        shadow_score = (1.0 - min(shadow_pct / 100.0, 1.0)) * 10.0
        quality_score = cloud_score + valid_score + snow_score + shadow_score

        return {
            "cloud_pct": round(cloud_pct, 2),
            "shadow_pct": round(shadow_pct, 2),
            "snow_land_pct": round(snow_land_pct, 2),
            "valid_pct": round(valid_pct, 2),
            "quality_score": round(quality_score, 1),
        }

    except Exception as exc:
        print(f"  [WARN] SCL quality metrics failed for {date}: {exc}")
        return default_metrics


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
    """Fetch marine conditions from Open-Meteo for a specific date at ~15 UTC.

    Sentinel-2 overpass for Nova Scotia is ~15:00 UTC (11:00 AM AST).

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

    # Sentinel-2 overpass at ~15 UTC (11:00 AM AST = 15:00 UTC)
    idx = min(15, len(times) - 1)

    return {
        "swell_height_m": hourly.get("swell_wave_height", [None])[idx],
        "swell_period_s": hourly.get("swell_wave_period", [None])[idx],
        "swell_direction_deg": hourly.get("swell_wave_direction", [None])[idx],
        "wave_height_m": hourly.get("wave_height", [None])[idx],
    }


# ---------------------------------------------------------------------------
# Single-spot processing
# ---------------------------------------------------------------------------
def process_spot(config: dict, args: argparse.Namespace) -> dict:
    """Process foam detection for a single spot config.

    Returns the output payload dict.
    """
    import ee

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
        print("WARNING: No segments found in bbox. Check your config bbox against ns_segments.geojson.")
        # Return empty manifest rather than exiting — allows --all-spots to continue
        return _build_empty_payload(config, slug, bbox, lat, lon)

    # Get clear scene dates
    print(f"Querying clear scenes (post-{MIN_DATE}, <{MAX_CLOUD_PERCENT}% cloud)...")
    scene_dates = get_clear_scene_dates(bbox, MAX_CLOUD_PERCENT, MIN_DATE)
    print(f"Clear scenes available: {len(scene_dates)}")

    if args.limit:
        scene_dates = scene_dates[: args.limit]
        print(f"Limited to first {args.limit} scenes")

    if not scene_dates:
        print("WARNING: No clear scenes found.")
        return _build_empty_payload(config, slug, bbox, lat, lon)

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
    quality_cache: dict[str, dict] = {}
    scene_quality_summary: list[dict] = []
    errors = 0

    for i, date in enumerate(scene_dates):
        # Fetch conditions for this date (once per date, shared across segments)
        if not args.skip_conditions and date not in conditions_cache:
            conditions_cache[date] = get_marine_conditions_for_date(lat, lon, date)
            time.sleep(METEO_PAUSE_S)

        # Compute SCL quality metrics for this scene (once per date)
        if date not in quality_cache:
            quality_cache[date] = get_scl_quality_metrics(date, bbox)
            time.sleep(GEE_PAUSE_S)

        conditions = conditions_cache.get(date, {})
        quality = quality_cache[date]
        swell_h = conditions.get("swell_height_m")
        swell_p = conditions.get("swell_period_s")
        swell_d = conditions.get("swell_direction_deg")

        qs = quality.get("quality_score")
        swell_str = f"{swell_h}m" if swell_h is not None else "N/A"
        qs_str = f"qs={qs:.0f}" if qs is not None else "qs=?"
        print(f"[{i + 1}/{len(scene_dates)}] {date} (swell: {swell_str}, {qs_str}, cloud={quality.get('cloud_pct')}%, valid={quality.get('valid_pct')}%)")

        # Record scene-level quality entry
        scene_quality_summary.append({
            "date": date,
            **quality,
        })

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
                # SCL quality metrics (scene-level, repeated per detection for easy filtering)
                "cloud_pct": quality.get("cloud_pct"),
                "shadow_pct": quality.get("shadow_pct"),
                "snow_land_pct": quality.get("snow_land_pct"),
                "valid_pct": quality.get("valid_pct"),
                "quality_score": quality.get("quality_score"),
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
            "quality": {
                "scenes_high_quality": sum(
                    1 for q in scene_quality_summary
                    if (q.get("quality_score") or 0) >= QUALITY_HIGH_THRESHOLD
                ),
                "scenes_usable": sum(
                    1 for q in scene_quality_summary
                    if (q.get("quality_score") or 0) >= QUALITY_USABLE_THRESHOLD
                ),
                "scenes_discarded": sum(
                    1 for q in scene_quality_summary
                    if (q.get("quality_score") or 0) < QUALITY_DISCARD_THRESHOLD
                ),
                "mean_quality_score": (
                    round(
                        sum(q["quality_score"] for q in scene_quality_summary if q.get("quality_score") is not None)
                        / max(1, sum(1 for q in scene_quality_summary if q.get("quality_score") is not None)),
                        1,
                    )
                    if scene_quality_summary else None
                ),
            },
        },
        "scene_quality": scene_quality_summary,
        "detections": detections,
    }

    write_json(output_path, payload)
    print(f"\nManifest saved to {output_path}")
    return payload


def _build_empty_payload(config: dict, slug: str, bbox: list, lat, lon) -> dict:
    """Build an empty result payload for spots with no segments or scenes."""
    run_id = generate_run_id()
    return {
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
        "parameters": {},
        "summary": {
            "scenes_processed": 0,
            "segments_processed": 0,
            "total_detections": 0,
            "errors": 0,
            "scenes_with_foam": 0,
            "date_range": {"start": None, "end": None},
            "quality": {
                "scenes_high_quality": 0,
                "scenes_usable": 0,
                "scenes_discarded": 0,
                "mean_quality_score": None,
            },
        },
        "scene_quality": [],
        "detections": [],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NIR foam detection per coastline segment across Sentinel-2 archive."
    )

    spot_group = parser.add_mutually_exclusive_group()
    spot_group.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to spot config JSON. Default: {DEFAULT_CONFIG_PATH}",
    )
    spot_group.add_argument(
        "--all-spots",
        action="store_true",
        help="Process ALL config files in pipeline/configs/ sequentially.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Max number of scenes to process per spot (for testing). Default: all.",
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
        help="Override output path (ignored when --all-spots is set).",
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

    # Initialize GEE once (shared across all spots)
    print("=" * 60)
    print("Phase 2.5: NIR Foam Detection")
    print("=" * 60)
    print("\nInitializing Google Earth Engine...")
    init_gee(args.project)

    # Determine which configs to process
    if args.all_spots:
        configs_dir = Path(__file__).resolve().parents[1] / "configs"
        config_paths = sorted(configs_dir.glob("*.json"))
        if not config_paths:
            print(f"ERROR: No config files found in {configs_dir}")
            sys.exit(1)
        print(f"All-spots mode: found {len(config_paths)} configs")
        if args.output:
            print("WARNING: --output is ignored in --all-spots mode")
    else:
        config_paths = [args.config]

    all_results: list[dict] = []
    failed_spots: list[str] = []

    for config_path in config_paths:
        print(f"\n{'=' * 60}")
        print(f"Processing: {config_path.name}")
        print("=" * 60)

        try:
            config = load_region_config(config_path)
        except Exception as exc:
            print(f"ERROR loading config {config_path}: {exc}")
            failed_spots.append(str(config_path))
            continue

        try:
            payload = process_spot(config, args)
            all_results.append({
                "slug": config["slug"],
                "name": config["name"],
                "scenes_processed": payload["summary"]["scenes_processed"],
                "total_detections": payload["summary"]["total_detections"],
                "mean_quality_score": payload["summary"]["quality"].get("mean_quality_score"),
            })
        except Exception as exc:
            print(f"ERROR processing {config.get('slug', config_path.name)}: {exc}")
            failed_spots.append(str(config_path))

    # Print summary for --all-spots runs
    if args.all_spots:
        print(f"\n{'=' * 60}")
        print("ALL-SPOTS SUMMARY")
        print("=" * 60)
        print(f"{'Spot':<35} {'Scenes':>8} {'Detections':>12} {'Avg Quality':>12}")
        print("-" * 60)
        for r in all_results:
            qs = f"{r['mean_quality_score']:.1f}" if r["mean_quality_score"] is not None else "N/A"
            print(f"{r['name']:<35} {r['scenes_processed']:>8} {r['total_detections']:>12} {qs:>12}")
        if failed_spots:
            print(f"\nFailed ({len(failed_spots)}):")
            for s in failed_spots:
                print(f"  - {s}")
        total_detections = sum(r["total_detections"] for r in all_results)
        print(f"\nTotal: {len(all_results)} spots, {total_detections} detections, {len(failed_spots)} failures")
    else:
        # Single-spot mode: print results summary inline
        if all_results:
            r = all_results[0]
            slug = config_paths[0].stem
            payload_summary = all_results[0]

            print(f"\n{'=' * 60}")
            print(f"RESULTS")
            print(f"{'=' * 60}")
            print(f"Scenes processed:  {r['scenes_processed']}")
            print(f"Total detections:  {r['total_detections']}")
            qs = r.get("mean_quality_score")
            if qs is not None:
                print(f"Mean quality score: {qs:.1f}")


if __name__ == "__main__":
    main()
