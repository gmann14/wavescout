#!/usr/bin/env python3
"""Script 18: Generate satellite gallery for atlas sections.

Adapted from script 16 (generate_gallery_fast.py). Queries GEE for clear
Sentinel-2 scenes, fetches swell conditions, picks best per swell bin,
and exports RGB + NIR thumbnails for atlas coastline sections.

Usage:
    python3 pipeline/scripts/18_generate_atlas_fast.py --section atlas-0001
    python3 pipeline/scripts/18_generate_atlas_fast.py --all
    python3 pipeline/scripts/18_generate_atlas_fast.py --all --limit 10 --min-score 60
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ee
import requests

from _script_utils import (
    generate_run_id,
    get_code_version,
    init_gee,
    now_utc_iso,
    write_json,
)

ATLAS_CONFIGS_DIR = Path("pipeline/configs/atlas")
ATLAS_GALLERY_DIR = Path("pipeline/data/atlas/gallery")
TIDE_STATIONS_PATH = Path("pipeline/data/tide_stations.json")

# --- Constants (same as script 16) ---
MIN_DATE = "2021-10-01"  # Open-Meteo swell data starts here for NS
MAX_CLOUD_PERCENT = 15.0
MIN_GALLERY_QS = 90
MIN_PERIOD_S = 8.0
OVERPASS_HOUR_UTC = 15
IMAGE_WIDTH = 800  # Keep consistent with spot gallery
PIXEL_SIZE_M = 10
OPENMETEO_DELAY_S = 0.12
MAX_RETRIES = 3
RETRY_DELAY_S = 10

SWELL_BINS = [
    ("glass", 0.0, 0.3),
    ("flat", 0.3, 0.6),
    ("small-", 0.6, 0.8),
    ("small", 0.8, 1.0),
    ("small+", 1.0, 1.2),
    ("moderate", 1.2, 1.5),
    ("moderate+", 1.5, 1.8),
    ("big", 1.8, 2.2),
    ("big+", 2.2, 2.8),
    ("storm", 2.8, 3.5),
    ("storm+", 3.5, 5.0),
    ("xxl", 5.0, 99.0),
]

RGB_VIS = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000, "gamma": 1.3}
NIR_VIS = {"bands": ["B8", "B8", "B8"], "min": 0, "max": 2000, "gamma": 1.4}

# SCL class constants
SCL_NO_DATA = 0
SCL_CLOUD_SHADOW = 3
SCL_WATER = 6
SCL_CLOUD_MEDIUM = 8
SCL_CLOUD_HIGH = 9
SCL_THIN_CIRRUS = 10
SCL_SNOW_ICE = 11


# --- GEE scene queries ---

def get_clear_scene_dates(bbox: list[float]) -> list[str]:
    """Query GEE for clear Sentinel-2 scene dates within bbox."""
    roi = ee.Geometry.Rectangle(bbox)
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(MIN_DATE, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PERCENT))
    )
    dates = (
        collection.aggregate_array("system:time_start")
        .map(lambda t: ee.Date(t).format("YYYY-MM-dd"))
        .distinct()
        .sort()
        .getInfo()
    )
    return dates


def get_scl_quality(date: str, bbox: list[float]) -> dict:
    """Compute SCL quality metrics for a scene."""
    defaults = {"cloud_pct": None, "snow_land_pct": None, "valid_pct": None, "quality_score": None}
    try:
        roi = ee.Geometry.Rectangle(bbox)
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(roi)
            .filterDate(date, ee.Date(date).advance(1, "day"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PERCENT))
            .sort("CLOUDY_PIXEL_PERCENTAGE")
        )
        if collection.size().getInfo() == 0:
            return defaults

        scl = collection.first().select("SCL")
        histogram = scl.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=roi,
            scale=PIXEL_SIZE_M,
            maxPixels=1e8,
        ).getInfo()

        hist = histogram.get("SCL", {})
        if not hist:
            return defaults

        total = sum(hist.values())
        if total == 0:
            return defaults

        cloud_px = sum(hist.get(str(c), 0) for c in [SCL_CLOUD_MEDIUM, SCL_CLOUD_HIGH, SCL_THIN_CIRRUS])
        shadow_px = hist.get(str(SCL_CLOUD_SHADOW), 0)
        snow_px = hist.get(str(SCL_SNOW_ICE), 0)
        water_px = hist.get(str(SCL_WATER), 0)
        nodata_px = hist.get(str(SCL_NO_DATA), 0)

        valid_px = total - nodata_px
        non_water_px = valid_px - water_px

        cloud_pct = (cloud_px / total) * 100
        valid_pct = (valid_px / total) * 100
        snow_land_pct = (snow_px / max(non_water_px, 1)) * 100
        shadow_pct = (shadow_px / total) * 100

        qs = (
            (1.0 - min(cloud_pct / 100, 1.0)) * 40
            + min(valid_pct / 100, 1.0) * 30
            + (1.0 - min(snow_land_pct / 100, 1.0)) * 20
            + (1.0 - min(shadow_pct / 100, 1.0)) * 10
        )

        return {
            "cloud_pct": round(cloud_pct, 2),
            "snow_land_pct": round(snow_land_pct, 2),
            "valid_pct": round(valid_pct, 2),
            "quality_score": round(qs, 1),
        }
    except Exception as e:
        print(f"      SCL quality failed for {date}: {e}")
        return defaults


# --- Open-Meteo conditions ---

def get_swell_conditions(lat: float, lon: float, date: str) -> dict:
    """Fetch swell conditions from Open-Meteo for a date at ~15 UTC."""
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date,
        "end_date": date,
        "hourly": "swell_wave_height,swell_wave_period,swell_wave_direction",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        hourly = resp.json().get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            return {"swell_height_m": None, "swell_period_s": None, "swell_direction_deg": None}
        idx = min(OVERPASS_HOUR_UTC, len(times) - 1)
        return {
            "swell_height_m": hourly.get("swell_wave_height", [None])[idx],
            "swell_period_s": hourly.get("swell_wave_period", [None])[idx],
            "swell_direction_deg": hourly.get("swell_wave_direction", [None])[idx],
        }
    except Exception:
        return {"swell_height_m": None, "swell_period_s": None, "swell_direction_deg": None}


def get_conditions_batch(lat: float, lon: float, dates: list[str]) -> dict[str, dict]:
    """Fetch swell conditions for multiple dates efficiently (batched by month)."""
    from collections import defaultdict

    results = {}
    by_month: dict[str, list[str]] = defaultdict(list)
    for d in dates:
        by_month[d[:7]].append(d)

    for month_key in sorted(by_month.keys()):
        month_dates = by_month[month_key]
        start = min(month_dates)
        end = max(month_dates)

        url = "https://marine-api.open-meteo.com/v1/marine"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start,
            "end_date": end,
            "hourly": "swell_wave_height,swell_wave_period,swell_wave_direction",
        }
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            hourly = resp.json().get("hourly", {})
            times = hourly.get("time", [])
            heights = hourly.get("swell_wave_height", [])
            periods = hourly.get("swell_wave_period", [])
            directions = hourly.get("swell_wave_direction", [])

            for i, t in enumerate(times):
                date_str = t[:10]
                hour = int(t[11:13]) if len(t) > 11 else 0
                if hour == OVERPASS_HOUR_UTC and date_str in month_dates:
                    results[date_str] = {
                        "swell_height_m": heights[i] if i < len(heights) else None,
                        "swell_period_s": periods[i] if i < len(periods) else None,
                        "swell_direction_deg": directions[i] if i < len(directions) else None,
                    }
        except Exception as e:
            print(f"    Open-Meteo batch failed for {month_key}: {e}")

        time.sleep(OPENMETEO_DELAY_S)

    for d in dates:
        if d not in results:
            results[d] = get_swell_conditions(lat, lon, d)
            time.sleep(OPENMETEO_DELAY_S)

    return results


# --- Tide lookup ---

def load_tide_stations() -> dict:
    """Load tide station mappings."""
    if TIDE_STATIONS_PATH.exists():
        with open(TIDE_STATIONS_PATH) as f:
            return json.load(f)
    return {}


def lookup_tide(station_id: str, date_str: str) -> dict | None:
    """Query CHS API for predicted tide at overpass time."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        start = dt.replace(hour=OVERPASS_HOUR_UTC - 1)
        end = dt.replace(hour=OVERPASS_HOUR_UTC + 1)

        url = f"https://api-iwls.dfo-mpo.gc.ca/api/v1/stations/{station_id}/data"
        resp = requests.get(url, params={
            "time-series-code": "wlp",
            "from": start.strftime("%Y-%m-%dT%H:%M:00Z"),
            "to": end.strftime("%Y-%m-%dT%H:%M:00Z"),
        }, timeout=10)

        if resp.status_code != 200:
            return None

        data = resp.json()
        if not data:
            return None

        target = dt.replace(hour=OVERPASS_HOUR_UTC)
        closest = min(data, key=lambda x: abs(
            datetime.fromisoformat(x["eventDate"].replace("Z", "+00:00")).replace(tzinfo=None) - target
        ))

        tide_m = closest.get("value")
        if tide_m is None:
            return None

        values = [d["value"] for d in data if d.get("value") is not None]
        if len(values) >= 2:
            lo, hi = min(values), max(values)
            mid = (lo + hi) / 2
            if tide_m > mid + (hi - mid) * 0.3:
                state = "high"
            elif tide_m < mid - (mid - lo) * 0.3:
                state = "low"
            else:
                state = "mid"
        else:
            state = "unknown"

        return {"tide_m": round(tide_m, 2), "tide_state": state}
    except Exception:
        return None


# --- Scene selection ---

def wave_energy(h: float, t: float) -> float:
    """Compute wave energy flux (W/m) from height and period."""
    return (1025 * 9.81**2 * h**2 * t) / (64 * math.pi)


def pick_best_scenes(scenes: dict[str, dict]) -> list[dict]:
    """Pick best scene per swell bin. Prefer period >= 8s, then highest QS."""
    binned: dict[str, list[tuple[str, dict]]] = {label: [] for label, _, _ in SWELL_BINS}

    for date, info in scenes.items():
        qs = info.get("quality_score") or 0
        if qs < MIN_GALLERY_QS:
            continue
        swell = info.get("swell_height_m")
        if swell is None:
            continue
        for label, lo, hi in SWELL_BINS:
            if lo <= swell < hi:
                binned[label].append((date, info))
                break

    picks = []
    for label, _, _ in SWELL_BINS:
        candidates = binned[label]
        if not candidates:
            continue
        long_period = [(d, i) for d, i in candidates if (i.get("swell_period_s") or 0) >= MIN_PERIOD_S]
        pool = long_period if long_period else candidates
        best_date, best_info = max(pool, key=lambda x: x[1].get("quality_score", 0))
        picks.append({
            "date": best_date,
            "bin_label": label,
            **best_info,
        })
    return picks


# --- Image export ---

def fetch_thumbnail(url: str) -> bytes | None:
    """Fetch thumbnail image from GEE URL with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=120)
            if resp.status_code == 200:
                return resp.content
            if resp.status_code == 429:
                time.sleep(RETRY_DELAY_S * (attempt + 1))
                continue
        except requests.RequestException:
            pass
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY_S)
    return None


def export_thumbnails(date_str: str, bbox: list[float], slug: str, swell: float, outdir: Path) -> dict:
    """Export RGB + NIR thumbnails for a scene."""
    ee_bbox = ee.Geometry.Rectangle(bbox)
    start = ee.Date(date_str)
    end = start.advance(1, "day")

    scenes = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(ee_bbox)
        .filterDate(start, end)
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    if scenes.size().getInfo() == 0:
        return {"rgb_path": None, "nir_path": None}

    image = ee.Image(scenes.first())
    results = {}
    swell_str = f"{swell:.1f}"

    for kind, vis in [("rgb", RGB_VIS), ("nir", NIR_VIS)]:
        fname = f"{slug}_{date_str}_{swell_str}m_{kind}.png"
        outpath = outdir / fname

        print(f"    {kind.upper()} ... ", end="", flush=True)
        try:
            url = image.getThumbURL({**vis, "dimensions": IMAGE_WIDTH, "region": ee_bbox, "format": "png"})
        except ee.EEException as e:
            print(f"GEE error: {e}")
            results[f"{kind}_path"] = None
            continue

        data = fetch_thumbnail(url)
        if data:
            outpath.parent.mkdir(parents=True, exist_ok=True)
            outpath.write_bytes(data)
            print(f"OK ({len(data) // 1024}KB)")
            results[f"{kind}_path"] = str(outpath)
        else:
            print("FAILED")
            results[f"{kind}_path"] = None

    return results


# --- Main processing ---

def process_section(slug: str, config: dict, tide_stations: dict) -> dict | None:
    """Process a single atlas section: query scenes, get conditions, select best, export images."""
    section_name = config.get("name", slug)
    bbox = config["bbox"]
    point = config.get("point", {})
    lat = point.get("lat")
    lon = point.get("lon")

    if not lat or not lon:
        lat = (bbox[1] + bbox[3]) / 2
        lon = (bbox[0] + bbox[2]) / 2

    metadata = config.get("atlas_metadata", {})

    # Step 1: Get clear scene dates from GEE
    print(f"    Querying clear scenes...", end=" ", flush=True)
    dates = get_clear_scene_dates(bbox)
    print(f"{len(dates)} dates")

    if not dates:
        print(f"    No clear scenes found")
        return None

    # Step 2: Get swell conditions (batched by month)
    print(f"    Fetching swell conditions...", end=" ", flush=True)
    conditions = get_conditions_batch(lat, lon, dates)
    valid_dates = [d for d in dates if conditions.get(d, {}).get("swell_height_m") is not None]
    print(f"{len(valid_dates)} with swell data")

    if not valid_dates:
        print(f"    No dates with swell data")
        return None

    # Step 3: Pre-filter candidates and get SCL quality
    print(f"    Computing quality scores...", end=" ", flush=True)

    scenes_raw = {}
    for d in valid_dates:
        cond = conditions[d]
        scenes_raw[d] = {
            "swell_height_m": cond["swell_height_m"],
            "swell_period_s": cond.get("swell_period_s"),
            "swell_direction_deg": cond.get("swell_direction_deg"),
        }

    # Find top 3 candidates per swell bin
    candidates_to_check: set[str] = set()
    binned_raw: dict[str, list[str]] = {label: [] for label, _, _ in SWELL_BINS}
    for d, info in scenes_raw.items():
        swell = info["swell_height_m"]
        for label, lo, hi in SWELL_BINS:
            if lo <= swell < hi:
                binned_raw[label].append(d)
                break

    for label, dates_in_bin in binned_raw.items():
        if not dates_in_bin:
            continue
        scored = []
        for d in dates_in_bin:
            period = scenes_raw[d].get("swell_period_s") or 0
            scored.append((d, period))
        scored.sort(key=lambda x: (-x[1], x[0]))
        for d, _ in scored[:3]:
            candidates_to_check.add(d)

    quality_cache = {}
    for i, d in enumerate(sorted(candidates_to_check)):
        qs = get_scl_quality(d, bbox)
        quality_cache[d] = qs
        if (i + 1) % 10 == 0:
            print(f"{i+1}/{len(candidates_to_check)}...", end=" ", flush=True)
    print(f"{len(candidates_to_check)} checked")

    # Build final scenes dict
    scenes = {}
    for d in candidates_to_check:
        cond = conditions[d]
        qs_info = quality_cache.get(d, {})
        scenes[d] = {
            "swell_height_m": cond["swell_height_m"],
            "swell_period_s": cond.get("swell_period_s"),
            "swell_direction_deg": cond.get("swell_direction_deg"),
            "cloud_pct": qs_info.get("cloud_pct", 0),
            "snow_land_pct": qs_info.get("snow_land_pct", 0),
            "valid_pct": qs_info.get("valid_pct", 100),
            "quality_score": qs_info.get("quality_score", 0),
        }

    # Step 4: Pick best scenes per swell bin
    picks = pick_best_scenes(scenes)
    if not picks:
        print(f"    No scenes pass quality filter")
        return None

    print(f"\n{'='*60}")
    print(f"  {section_name} — {len(picks)} scenes selected")
    for p in picks:
        print(f"    {p['bin_label']:>10}: {p['date']} ({p['swell_height_m']:.1f}m, "
              f"period={p.get('swell_period_s', '?')}s, qs={p.get('quality_score', 0):.0f})")
    print()

    # Step 5: Export images
    outdir = ATLAS_GALLERY_DIR / slug
    outdir.mkdir(parents=True, exist_ok=True)

    # Find nearest tide station (use first known station as fallback)
    station_id = None
    for station_slug, station_info in tide_stations.items():
        if station_info.get("station_id"):
            station_id = station_info["station_id"]
            break

    section_scenes = []
    for p in picks:
        date_str = p["date"]
        swell = p["swell_height_m"]

        print(f"  [{p['bin_label']}] {date_str} ({swell:.1f}m):")
        paths = export_thumbnails(date_str, bbox, slug, swell, outdir)

        tide_info = lookup_tide(station_id, date_str) if station_id else None

        section_scenes.append({
            "date": date_str,
            "swell_height_m": swell,
            "swell_period_s": p.get("swell_period_s"),
            "swell_direction_deg": p.get("swell_direction_deg"),
            "cloud_pct": p.get("cloud_pct", 0),
            "quality_score": p.get("quality_score", 0),
            "foam_fraction": 0,
            "wave_energy": wave_energy(swell, p.get("swell_period_s") or 8),
            "bin_label": p["bin_label"],
            "tide_m": tide_info["tide_m"] if tide_info else None,
            "tide_state": tide_info["tide_state"] if tide_info else None,
            "rgb_path": paths.get("rgb_path"),
            "nir_path": paths.get("nir_path"),
        })
        time.sleep(1)

    return {
        "section_id": slug,
        "section_name": section_name,
        "slug": slug,
        "mean_score": metadata.get("mean_score", 0),
        "max_score": metadata.get("max_score", 0),
        "segment_count": metadata.get("segment_count", 0),
        "segment_ids": metadata.get("segment_ids", []),
        "coastline_length_m": metadata.get("coastline_length_m", 0),
        "scenes": section_scenes,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate atlas section gallery images")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--section", help="Process a single section by ID")
    group.add_argument("--all", action="store_true", help="Process all atlas sections")
    parser.add_argument("--limit", type=int, help="Max sections to process")
    parser.add_argument("--min-score", type=float, default=50, help="Min mean score to process (default: 50)")
    args = parser.parse_args()

    init_gee()
    tide_stations = load_tide_stations()

    # Discover sections from configs
    if args.section:
        config_path = ATLAS_CONFIGS_DIR / f"{args.section}.json"
        if not config_path.exists():
            print(f"ERROR: No config for '{args.section}'")
            sys.exit(1)
        slugs = [args.section]
    else:
        slugs = sorted([p.stem for p in ATLAS_CONFIGS_DIR.glob("*.json")])
        if not slugs:
            print("ERROR: No atlas configs found. Run script 17 first.")
            sys.exit(1)

    # Filter by min score
    if args.min_score > 0:
        filtered_slugs = []
        for slug in slugs:
            config_path = ATLAS_CONFIGS_DIR / f"{slug}.json"
            with open(config_path) as f:
                config = json.load(f)
            score = config.get("atlas_metadata", {}).get("mean_score", 0)
            if score >= args.min_score:
                filtered_slugs.append(slug)
        slugs = filtered_slugs

    if args.limit:
        slugs = slugs[:args.limit]

    print(f"Atlas Gallery Generator")
    print(f"  Sections: {len(slugs)}")
    print(f"  Min score: {args.min_score}")
    print(f"  Output: {ATLAS_GALLERY_DIR}/")
    print()

    gallery_manifest = {
        "script": "18_generate_atlas_fast.py",
        "run_id": generate_run_id(),
        "generated_at_utc": now_utc_iso(),
        "code_version": get_code_version(),
        "parameters": {
            "image_width_px": IMAGE_WIDTH,
            "min_quality_score": MIN_GALLERY_QS,
            "min_period_preference_s": MIN_PERIOD_S,
            "min_mean_score": args.min_score,
            "swell_bins": {label: f"{lo}-{hi}m" for label, lo, hi in SWELL_BINS},
        },
        "sections": [],
    }

    total_images = 0
    for i, slug in enumerate(slugs, 1):
        config_path = ATLAS_CONFIGS_DIR / f"{slug}.json"
        with open(config_path) as f:
            config = json.load(f)
        score = config.get("atlas_metadata", {}).get("mean_score", 0)
        print(f"\n[{i}/{len(slugs)}] Processing {slug} (score: {score:.1f}) ...")

        result = process_section(slug, config, tide_stations)
        if result:
            gallery_manifest["sections"].append(result)
            total_images += sum(
                (1 if s.get("rgb_path") else 0) + (1 if s.get("nir_path") else 0)
                for s in result["scenes"]
            )

    gallery_manifest["summary"] = {
        "total_sections": len(gallery_manifest["sections"]),
        "total_images": total_images,
    }

    manifest_path = ATLAS_GALLERY_DIR / "manifest.json"
    write_json(manifest_path, gallery_manifest)

    print(f"\n{'='*60}")
    print(f"Done! {total_images} images across {len(gallery_manifest['sections'])} sections.")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
