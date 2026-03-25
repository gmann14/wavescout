#!/usr/bin/env python3
"""Generate true-color PNG thumbnails from GEE directly (no GeoTIFF download needed).

Outputs viewable RGB images scaled to 0-255 with a nice stretch.
"""

import argparse
import json
import os
from pathlib import Path

import ee
from PIL import Image
import numpy as np
import requests
from io import BytesIO

def main():
    parser = argparse.ArgumentParser(description="Generate true-color thumbnails from GEE")
    parser.add_argument("--config", required=True, help="Path to spot config JSON")
    parser.add_argument("--limit", type=int, default=5, help="Number of scenes to generate")
    parser.add_argument("--outdir", default="pipeline/data/thumbnails", help="Output directory")
    parser.add_argument("--width", type=int, default=1024, help="Image width in pixels")
    args = parser.parse_args()

    # Load env
    from dotenv import load_dotenv
    load_dotenv()
    project = os.getenv("GEE_PROJECT", "seotakeoff")
    ee.Initialize(project=project)

    config = json.load(open(args.config))
    slug = config["slug"]
    bbox_coords = config["bbox"]  # [west, south, east, north]
    bbox = ee.Geometry.Rectangle(bbox_coords)

    outdir = Path(args.outdir) / slug
    outdir.mkdir(parents=True, exist_ok=True)

    # Query clear scenes
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(bbox)
        .filterDate("2020-06-01", "2025-09-30")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 15))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
        .limit(args.limit)
    )

    image_list = collection.toList(args.limit)
    count = min(args.limit, collection.size().getInfo())
    print(f"Generating {count} thumbnails for {config['name']}\n")

    for i in range(count):
        image = ee.Image(image_list.get(i))
        date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd").getInfo()
        cloud_pct = image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()

        # True color (B4=Red, B3=Green, B2=Blue) with good visual stretch
        vis_params = {
            "bands": ["B4", "B3", "B2"],
            "min": 0,
            "max": 3000,
            "gamma": 1.3,
            "dimensions": args.width,
            "region": bbox,
            "format": "png",
        }

        url = image.getThumbURL(vis_params)
        print(f"  {slug}_{date} (cloud: {cloud_pct:.0f}%) ... ", end="", flush=True)

        resp = requests.get(url)
        if resp.status_code == 200:
            outpath = outdir / f"{slug}_{date}.png"
            with open(outpath, "wb") as f:
                f.write(resp.content)
            print(f"saved ({len(resp.content)//1024}KB)")
        else:
            print(f"FAILED ({resp.status_code})")

    print(f"\nThumbnails saved to {outdir}/")


if __name__ == "__main__":
    main()
