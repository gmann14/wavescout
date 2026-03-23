"""
Step 1.1: Test GEE access and count available Sentinel-2 imagery
for a configured test area.

Run examples:
    python3 pipeline/scripts/01_test_gee_access.py
    python3 pipeline/scripts/01_test_gee_access.py --config pipeline/configs/lawrencetown.json
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from _script_utils import (
    DEFAULT_CONFIG_PATH,
    default_manifest_path,
    init_gee,
    load_region_config,
    today_iso,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Earth Engine access and inventory Sentinel-2 scenes for a region config."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to region config JSON. Default: {DEFAULT_CONFIG_PATH}",
    )
    parser.add_argument(
        "--start-date",
        help="Override start date in YYYY-MM-DD format. Default: config date_range.start",
    )
    parser.add_argument(
        "--end-date",
        default=today_iso(),
        help="End date in YYYY-MM-DD format. Default: today",
    )
    parser.add_argument(
        "--cloud-max",
        type=float,
        default=30.0,
        help="Maximum scene cloud percentage for the clear-scene subset. Default: 30",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=20,
        help="Number of clear-scene dates to print in the console summary. Default: 20",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional manifest output path. Defaults to pipeline/data/manifests/<slug>_scene_inventory.json",
    )
    parser.add_argument(
        "--project",
        help="GEE cloud project ID. Default: GEE_PROJECT env var.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    import ee

    config = load_region_config(args.config)

    start_date = args.start_date or config["date_range"]["start"]
    end_date = args.end_date
    bbox_values = config["bbox"]

    init_gee(args.project)

    bbox = ee.Geometry.Rectangle(bbox_values)

    output_path = args.output or default_manifest_path(
        "scene_inventory", config["slug"]
    )

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(bbox)
        .filterDate(start_date, end_date)
    )

    total_count = collection.size().getInfo()
    clear_collection = collection.filter(
        ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", args.cloud_max)
    )
    clear_count = clear_collection.size().getInfo()

    dates = (
        clear_collection.aggregate_array("system:time_start")
        .map(lambda t: ee.Date(t).format("YYYY-MM-dd"))
        .getInfo()
    )

    print(f"Config: {config['name']} ({config['slug']})")
    print(f"BBox: {bbox_values}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Total Sentinel-2 images: {total_count}")
    print(f"Images with <{args.cloud_max:.0f}% cloud cover: {clear_count}")
    print(f"\nFirst clear image: {dates[0] if dates else 'none'}")
    print(f"Last clear image: {dates[-1] if dates else 'none'}")
    print(f"\nSample clear dates (first {min(args.sample_limit, len(dates))}):")
    for date in dates[: args.sample_limit]:
        print(f"  {date}")

    band_names = None
    if clear_count > 0:
        sample = clear_collection.first()
        band_names = sample.bandNames().getInfo()
        print(f"\nAvailable bands: {band_names}")
        print("\nKey bands for wave detection:")
        print("  B3 (Green, 560nm) - foam/whitecap detection numerator")
        print("  B4 (Red, 665nm) - foam/whitecap detection denominator")
        print("  B8 (NIR, 842nm) - water/land discrimination")
        print("  SCL - Scene Classification Layer (for cloud masking)")

    payload = {
        "script": "01_test_gee_access.py",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": config["_config_path"],
        "region": {
            "name": config["name"],
            "slug": config["slug"],
            "region": config.get("region"),
            "bbox": bbox_values,
            "point": config.get("point"),
        },
        "query": {
            "start_date": start_date,
            "end_date": end_date,
            "cloud_max": args.cloud_max,
        },
        "summary": {
            "total_scene_count": total_count,
            "clear_scene_count": clear_count,
            "first_clear_date": dates[0] if dates else None,
            "last_clear_date": dates[-1] if dates else None,
        },
        "clear_scene_dates": dates,
        "available_bands": band_names,
    }
    write_json(output_path, payload)
    print(f"\nManifest saved to {output_path}")


if __name__ == "__main__":
    main()
