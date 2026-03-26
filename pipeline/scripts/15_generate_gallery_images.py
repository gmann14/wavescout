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

SWELL_BINS = [
    ("flat", 0.0, 0.5),
    ("small", 0.5, 1.0),
    ("moderate", 1.0, 1.5),
    ("big", 1.5, 2.5),
    ("storm", 2.5, 99.0),
]

IMAGE_WIDTH = 800

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


def aggregate_scene_foam(detections: list[dict]) -> dict[str, dict]:
    """Aggregate foam detections by date, computing max foam fraction per scene.

    Returns {date: {swell_height_m, max_foam_fraction, mean_foam_fraction, segment_count}}.
    """
    by_date: dict[str, list[dict]] = {}
    for d in detections:
        date = d.get("date")
        if not date:
            continue
        by_date.setdefault(date, []).append(d)

    scenes = {}
    for date, dets in by_date.items():
        fractions = [d["foam_fraction"] for d in dets if d.get("foam_fraction") is not None]
        if not fractions:
            continue
        swell = dets[0].get("swell_height_m")
        if swell is None:
            continue
        scenes[date] = {
            "swell_height_m": swell,
            "max_foam_fraction": max(fractions),
            "mean_foam_fraction": sum(fractions) / len(fractions),
            "segment_count": len(dets),
        }
    return scenes


def pick_representative_scenes(
    scenes: dict[str, dict], limit: int | None = None
) -> list[dict]:
    """Pick up to one scene per swell bin, choosing highest foam fraction.

    Returns list of {date, swell_height_m, foam_fraction, bin_label}.
    """
    binned: dict[str, list[tuple[str, dict]]] = {label: [] for label, _, _ in SWELL_BINS}

    for date, info in scenes.items():
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
        # Pick the scene with highest max foam fraction in this bin
        best_date, best_info = max(candidates, key=lambda x: x[1]["max_foam_fraction"])
        picks.append({
            "date": best_date,
            "swell_height_m": best_info["swell_height_m"],
            "foam_fraction": best_info["max_foam_fraction"],
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
        print(f"    {p['bin_label']:>10}: {p['date']} ({p['swell_height_m']:.1f}m swell, foam={p['foam_fraction']:.4f})")
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

        scene_entry = {
            "date": date_str,
            "swell_height_m": swell,
            "foam_fraction": p["foam_fraction"],
            "bin_label": p["bin_label"],
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
