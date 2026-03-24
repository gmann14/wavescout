"""
Step 1.2: Export sample Sentinel-2 images for visual inspection.

Run examples:
    python3 pipeline/scripts/02_export_sample_images.py
    python3 pipeline/scripts/02_export_sample_images.py --limit 10
    python3 pipeline/scripts/02_export_sample_images.py --config pipeline/configs/lawrencetown.json
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
        description="Export sample Sentinel-2 scenes for a configured region."
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
        default=20.0,
        help="Maximum scene cloud percentage for exports. Default: 20",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of scenes to export. Default: 20",
    )
    parser.add_argument(
        "--drive-folder",
        help="Override Google Drive folder. Default: config export.drive_folder",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=10,
        help="Export scale in meters. Default: 10",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional manifest output path. Defaults to pipeline/data/manifests/<slug>_export_manifest.json",
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
    drive_folder = args.drive_folder or config.get("export", {}).get(
        "drive_folder", "wavescout_samples"
    )
    output_path = args.output or default_manifest_path(
        "export_manifest", config["slug"]
    )

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(bbox)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", args.cloud_max))
        .sort("system:time_start", False)
    )

    bands = ["B2", "B3", "B4", "B8", "B11", "SCL"]
    image_list = collection.toList(args.limit)
    count = min(args.limit, collection.size().getInfo())

    print(f"Config: {config['name']} ({config['slug']})")
    print(f"Exporting {count} image(s) to Google Drive folder: {drive_folder}\n")

    exports = []
    for i in range(count):
        raw = ee.Image(image_list.get(i)).select(bands)
        # Cast all bands to UInt16 (SCL is Byte, spectral bands are UInt16)
        image = raw.toUint16()
        date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd").getInfo()
        cloud_pct = image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()
        product_id = image.get("PRODUCT_ID").getInfo()
        system_index = image.get("system:index").getInfo()

        task_name = f"{config['slug']}_{date}"
        print(f"  Exporting: {task_name} (cloud: {cloud_pct:.0f}%)")

        task = ee.batch.Export.image.toDrive(
            image=image.clip(bbox),
            description=task_name,
            folder=drive_folder,
            region=bbox,
            scale=args.scale,
            maxPixels=1e8,
            fileFormat="GeoTIFF",
        )
        task.start()

        exports.append(
            {
                "description": task_name,
                "date": date,
                "cloud_pct": cloud_pct,
                "product_id": product_id,
                "system_index": system_index,
                "task_id": getattr(task, "id", None),
            }
        )

    payload = {
        "script": "02_export_sample_images.py",
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
            "limit": args.limit,
            "scale": args.scale,
            "bands": bands,
            "drive_folder": drive_folder,
        },
        "exports": exports,
    }
    write_json(output_path, payload)

    print(f"\n{count} export task(s) started.")
    print("Monitor progress at: https://code.earthengine.google.com/tasks")
    print(f"Files will appear in Google Drive > {drive_folder}/")
    print(f"Manifest saved to {output_path}")


if __name__ == "__main__":
    main()
