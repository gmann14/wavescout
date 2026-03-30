#!/usr/bin/env python3
"""Phase 3, Script 15: Generate representative satellite gallery images for the web viewer.

For each spot with foam detection data, picks up to 5 representative scenes
across swell bins (flat, small, moderate, big, storm), choosing the scene
with the highest foam fraction per bin for visual interest.

Generates two thumbnails per scene via GEE:
  - True-color RGB (B4/B3/B2) — what it looks like to the human eye
  - NIR single-band (B8) — what the algorithm sees (water=black, foam=white)

Output: pipeline/data/gallery/{spot-name}/{spot}_{date}_{swell}m_rgb.png
        pipeline/data/gallery/{spot-name}/{spot}_{date}_{swell}m_nir.png
        pipeline/data/gallery/manifest.json

Usage:
    python3 pipeline/scripts/15_generate_gallery_images.py --spot lawrencetown-beach
    python3 pipeline/scripts/15_generate_gallery_images.py --spot lawrencetown-beach --limit 2
    python3 pipeline/scripts/15_generate_gallery_images.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import ee
import requests
from datetime import datetime, timedelta

from _script_utils import (
    generate_run_id,
    get_code_version,
    init_gee,
    now_utc_iso,
    write_json,
)

MANIFESTS_DIR = Path("pipeline/data/manifests")
CONFIGS_DIR = Path("pipeline/configs")
GALLERY_DIR = Path("pipeline/data/gallery")
TIDE_STATIONS_PATH = Path("pipeline/data/tide_stations.json")
OVERPASS_HOUR_UTC = 15  # Sentinel-2 passes NS ~15:00 UTC

# --- Tide lookup ---

def load_tide_stations() -> dict:
    """Load tide station mapping {slug: {station_id, station_name, distance_km}}"""
    if TIDE_STATIONS_PATH.exists():
        return json.load(open(TIDE_STATIONS_PATH))
    return {}

def lookup_tide(station_id: str, date_str: str) -> dict | None:
    """Query CHS API for predicted tide at overpass time.
    Returns {tide_m, tide_state} or None on failure."""
    try:
        # Query 1-hour window around overpass
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
        
        # Find closest reading to overpass time
        target = dt.replace(hour=OVERPASS_HOUR_UTC)
        closest = min(data, key=lambda x: abs(
            datetime.fromisoformat(x["eventDate"].replace("Z", "+00:00")).replace(tzinfo=None) - target
        ))
        
        tide_m = closest.get("value")
        if tide_m is None:
            return None
        
        # Classify tide state based on local range
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
    except Exception as e:
        print(f"      tide lookup failed: {e}")
        return None

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

# Resolution settings
# Sentinel-2 native resolution is 10m/pixel
# We allow modest upscaling (up to 3x) for tighter views
# 800px is the sweet spot for most bboxes
IMAGE_WIDTH = 800  # fixed width for consistent output

RGB_VIS = {
    "bands": ["B4", "B3", "B2"],
    "min": 0,
    "max": 3000,
    "gamma": 1.3,
}

NIR_VIS = {
    "bands": ["B8", "B8", "B8"],
    "min": 0,
    "max": 2000,
    "gamma": 1.4,
}

MAX_RETRIES = 3
RETRY_DELAY_S = 10


def discover_spots() -> list[str]:
    """Find all spot slugs that have foam detection manifests."""
    slugs = []
    for path in sorted(MANIFESTS_DIR.glob("*_foam_detections.json")):
        slug = path.name.replace("_foam_detections.json", "")
        config_path = CONFIGS_DIR / f"{slug}.json"
        if config_path.exists():
            slugs.append(slug)
        else:
            print(f"  WARN: foam data for '{slug}' but no config, skipping")
    return slugs


def load_foam_manifest(slug: str) -> dict | None:
    """Load a spot's foam detection manifest."""
    path = MANIFESTS_DIR / f"{slug}_foam_detections.json"
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


def load_config(slug: str) -> dict:
    """Load a spot's config."""
    path = CONFIGS_DIR / f"{slug}.json"
    with path.open() as f:
        return json.load(f)


MIN_WATER_PIXELS = 50  # Segments with fewer water pixels are noise — exclude


def _wave_energy(h: float, t: float) -> float:
    """Simplified deep-water wave power flux in W/m (∝ H²T)."""
    import math
    return (1025 * 9.81**2 * h**2 * t) / (64 * math.pi)


def aggregate_scene_foam(detections: list[dict]) -> dict[str, dict]:
    """Aggregate foam detections by date, filtering noisy segments.

    Only includes segments with ≥ MIN_WATER_PIXELS water pixels.
    Returns {date: {swell_height_m, swell_period_s, wave_energy, quality_score,
                    max_foam_fraction, median_foam_fraction, segment_count, valid_segments}}.
    """
    by_date: dict[str, list[dict]] = {}
    for d in detections:
        date = d.get("date")
        if not date:
            continue
        by_date.setdefault(date, []).append(d)

    scenes = {}
    for date, dets in by_date.items():
        # Filter to segments with enough water pixels for reliable foam fractions
        valid_dets = [
            d for d in dets
            if d.get("foam_fraction") is not None
            and (d.get("water_pixel_count") or 0) >= MIN_WATER_PIXELS
        ]
        if not valid_dets:
            continue
        fractions = sorted([d["foam_fraction"] for d in valid_dets])
        swell = dets[0].get("swell_height_m")
        if swell is None:
            continue
        period = dets[0].get("swell_period_s") or 8.0
        direction = dets[0].get("swell_direction_deg")
        cloud = dets[0].get("cloud_pct", 0)
        snow = dets[0].get("snow_land_pct", 0)
        qs = dets[0].get("quality_score") or 0
        median_foam = fractions[len(fractions) // 2]
        scenes[date] = {
            "swell_height_m": swell,
            "swell_period_s": period,
            "swell_direction_deg": direction,
            "cloud_pct": cloud,
            "snow_land_pct": snow,
            "wave_energy": _wave_energy(swell, period),
            "quality_score": qs,
            "max_foam_fraction": max(fractions),
            "median_foam_fraction": median_foam,
            "mean_foam_fraction": sum(fractions) / len(fractions),
            "segment_count": len(dets),
            "valid_segments": len(valid_dets),
        }
    return scenes


MIN_GALLERY_QS = 90  # Minimum quality score for gallery scenes (lowered from 95 to capture bigger swell days)
MAX_SNOW_PCT = 10.0  # Exclude scenes with >10% snow on land (scale 0-100, winter contamination → false foam)
MIN_PERIOD_S = 8.0   # Prefer scenes with period ≥ 8s (cleaner swell, more defined waves)


def pick_representative_scenes(
    scenes: dict[str, dict], limit: int | None = None
) -> list[dict]:
    """Pick up to one scene per swell bin, balancing quality and foam visibility.

    Filters to scenes with quality_score ≥ MIN_GALLERY_QS, then picks the scene
    with the highest median foam fraction (robust to segment outliers).

    Returns list of {date, swell_height_m, foam_fraction, wave_energy, quality_score, bin_label}.
    """
    binned: dict[str, list[tuple[str, dict]]] = {label: [] for label, _, _ in SWELL_BINS}

    for date, info in scenes.items():
        # Filter by quality score — excludes cloudy/contaminated scenes
        if info.get("quality_score", 0) < MIN_GALLERY_QS:
            continue
        # NOTE: Winter scenes kept — best swell comes with winter storms.
        # Human can visually distinguish foam from snow/ice in imagery.
        # Require at least 2 valid segments for reliable aggregation
        if info.get("valid_segments", 0) < 2:
            continue
        swell = info["swell_height_m"]
        for label, lo, hi in SWELL_BINS:
            if lo <= swell < hi:
                binned[label].append((date, info))
                break

    picks = []
    for label, _, _ in SWELL_BINS:
        candidates = binned[label]
        if not candidates:
            continue
        # Prefer scenes with period ≥ MIN_PERIOD_S (cleaner, more defined swell)
        long_period = [(d, i) for d, i in candidates if (i.get("swell_period_s") or 0) >= MIN_PERIOD_S]
        pool = long_period if long_period else candidates
        # Pick scene with highest median foam (robust to noisy outlier segments)
        best_date, best_info = max(pool, key=lambda x: x[1]["median_foam_fraction"])
        picks.append({
            "date": best_date,
            "swell_height_m": best_info["swell_height_m"],
            "swell_period_s": best_info.get("swell_period_s"),
            "swell_direction_deg": best_info.get("swell_direction_deg"),
            "cloud_pct": best_info.get("cloud_pct", 0),
            "foam_fraction": best_info["median_foam_fraction"],
            "wave_energy": best_info.get("wave_energy", 0),
            "quality_score": best_info.get("quality_score", 0),
            "bin_label": label,
        })

    if limit is not None:
        picks = picks[:limit]
    return picks


def fetch_thumbnail_with_retry(url: str) -> bytes | None:
    """Fetch a thumbnail URL with retry on failure."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=120)
            if resp.status_code == 200:
                return resp.content
            if resp.status_code == 429:
                wait = RETRY_DELAY_S * (attempt + 1)
                print(f"rate limited, waiting {wait}s ... ", end="", flush=True)
                time.sleep(wait)
                continue
            print(f"HTTP {resp.status_code} ", end="", flush=True)
        except requests.RequestException as e:
            print(f"error: {e} ", end="", flush=True)
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY_S)
    return None


def find_scene_image(date_str: str, bbox: ee.Geometry) -> ee.Image | None:
    """Find the Sentinel-2 scene for a specific date within the bbox."""
    start = ee.Date(date_str)
    end = start.advance(1, "day")

    scenes = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(bbox)
        .filterDate(start, end)
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )

    count = scenes.size().getInfo()
    if count == 0:
        return None
    return ee.Image(scenes.first())





def generate_scene_thumbnails(
    image: ee.Image,
    bbox: ee.Geometry,
    slug: str,
    date_str: str,
    swell: float,
    outdir: Path,
) -> dict[str, str | None]:
    """Generate RGB and NIR thumbnails for a scene. Returns {rgb_path, nir_path}."""
    results = {}
    swell_str = f"{swell:.1f}"

    for kind, vis in [("rgb", RGB_VIS), ("nir", NIR_VIS)]:
        fname = f"{slug}_{date_str}_{swell_str}m_{kind}.png"
        outpath = outdir / fname

        vis_params = {
            **vis,
            "dimensions": IMAGE_WIDTH,
            "region": bbox,
            "format": "png",
        }

        print(f"    {kind.upper()} ... ", end="", flush=True)
        try:
            url = image.getThumbURL(vis_params)
        except ee.EEException as e:
            print(f"GEE error: {e}")
            results[f"{kind}_path"] = None
            continue

        data = fetch_thumbnail_with_retry(url)
        if data:
            outpath.parent.mkdir(parents=True, exist_ok=True)
            with open(outpath, "wb") as f:
                f.write(data)
            print(f"OK ({len(data) // 1024}KB)")
            results[f"{kind}_path"] = str(outpath)
        else:
            print("FAILED")
            results[f"{kind}_path"] = None

    return results


def process_spot(slug: str, limit: int | None = None) -> dict | None:
    """Process a single spot: pick scenes, generate thumbnails.

    Returns manifest entry for the spot, or None on failure.
    """
    manifest = load_foam_manifest(slug)
    if not manifest:
        print(f"  No foam manifest for {slug}")
        return None

    config = load_config(slug)
    spot_name = config.get("name", slug)
    bbox = ee.Geometry.Rectangle(config["bbox"])
    detections = manifest.get("detections", [])

    if not detections:
        print(f"  No detections for {slug}")
        return None

    scenes = aggregate_scene_foam(detections)
    picks = pick_representative_scenes(scenes, limit=limit)

    if not picks:
        print(f"  No representative scenes for {slug}")
        return None

    print(f"\n{'='*60}")
    print(f"  {spot_name} — {len(picks)} scenes selected")
    for p in picks:
        energy_kw = p.get('wave_energy', 0) / 1000
        qs = p.get('quality_score', 0)
        print(f"    {p['bin_label']:>10}: {p['date']} ({p['swell_height_m']:.1f}m swell, foam={p['foam_fraction']:.4f}, energy={energy_kw:.1f}kW/m, qs={qs:.0f})")
    print()

    outdir = GALLERY_DIR / slug
    outdir.mkdir(parents=True, exist_ok=True)

    spot_scenes = []
    for p in picks:
        date_str = p["date"]
        swell = p["swell_height_m"]

        print(f"  [{p['bin_label']}] {date_str} ({swell:.1f}m):")
        image = find_scene_image(date_str, bbox)
        if image is None:
            print(f"    No scene found for {date_str}, skipping")
            continue

        paths = generate_scene_thumbnails(image, bbox, slug, date_str, swell, outdir)

        # Lookup tide data
        tide_info = None
        tide_stations = load_tide_stations()
        station = tide_stations.get(slug)
        if station and station.get("station_id"):
            tide_info = lookup_tide(station["station_id"], date_str)
        
        scene_entry = {
            "date": date_str,
            "swell_height_m": swell,
            "swell_period_s": p.get("swell_period_s"),
            "swell_direction_deg": p.get("swell_direction_deg"),
            "cloud_pct": p.get("cloud_pct", 0),
            "foam_fraction": p["foam_fraction"],
            "quality_score": p.get("quality_score", 0),
            "wave_energy": p.get("wave_energy", 0),
            "bin_label": p["bin_label"],
            "tide_m": tide_info["tide_m"] if tide_info else None,
            "tide_state": tide_info["tide_state"] if tide_info else None,
            "rgb_path": paths.get("rgb_path"),
            "nir_path": paths.get("nir_path"),
        }
        spot_scenes.append(scene_entry)

        # Small delay between scenes to be nice to GEE
        time.sleep(1)

    return {
        "spot_name": spot_name,
        "slug": slug,
        "scenes": spot_scenes,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate representative gallery images for the WaveScout web viewer"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--spot", help="Process a single spot by slug")
    group.add_argument("--all", action="store_true", help="Process all spots with foam data")
    parser.add_argument("--limit", type=int, default=None, help="Max scenes per spot (for testing)")
    args = parser.parse_args()

    init_gee()

    # Determine spots to process
    if args.spot:
        config_path = CONFIGS_DIR / f"{args.spot}.json"
        if not config_path.exists():
            print(f"ERROR: No config found for '{args.spot}'")
            sys.exit(1)
        foam_path = MANIFESTS_DIR / f"{args.spot}_foam_detections.json"
        if not foam_path.exists():
            print(f"ERROR: No foam detection data for '{args.spot}'")
            sys.exit(1)
        slugs = [args.spot]
    else:
        slugs = discover_spots()
        if not slugs:
            print("ERROR: No spots with foam detection data found")
            sys.exit(1)

    print(f"Gallery Image Generator")
    print(f"  Spots: {len(slugs)}")
    print(f"  Limit: {args.limit or 'none (up to 5 per spot)'}")
    print(f"  Output: {GALLERY_DIR}/")

    run_id = generate_run_id()
    gallery_manifest = {
        "script": "15_generate_gallery_images.py",
        "run_id": run_id,
        "generated_at_utc": now_utc_iso(),
        "code_version": get_code_version(),
        "parameters": {
            "image_width_px": IMAGE_WIDTH,
            "swell_bins": {label: f"{lo}-{hi}m" for label, lo, hi in SWELL_BINS},
            "limit_per_spot": args.limit,
        },
        "spots": [],
    }

    # Load existing manifest to preserve previously-generated spots
    manifest_path = GALLERY_DIR / "manifest.json"
    existing_spots: dict[str, dict] = {}
    if manifest_path.exists():
        try:
            with manifest_path.open() as f:
                existing = json.load(f)
            for s in existing.get("spots", []):
                existing_spots[s["slug"]] = s
        except (json.JSONDecodeError, KeyError):
            pass

    total_images = 0
    for i, slug in enumerate(slugs, 1):
        print(f"\n[{i}/{len(slugs)}] Processing {slug} ...")
        result = process_spot(slug, limit=args.limit)
        if result:
            existing_spots[slug] = result
            total_images += sum(
                (1 if s.get("rgb_path") else 0) + (1 if s.get("nir_path") else 0)
                for s in result["scenes"]
            )

    # Write combined manifest with all spots (existing + newly processed)
    gallery_manifest["spots"] = list(existing_spots.values())
    gallery_manifest["summary"] = {
        "total_spots": len(existing_spots),
        "spots_processed_this_run": len(slugs),
        "total_images_generated": total_images,
    }
    write_json(manifest_path, gallery_manifest)

    print(f"\n{'='*60}")
    print(f"Done! Generated {total_images} images across {len(slugs)} spots.")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
