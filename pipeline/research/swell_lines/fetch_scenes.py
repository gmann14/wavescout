#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.research.swell_lines import (
    CALIBRATION_PAIRS_PATH,
    CHIPS_DIR,
    DEFAULT_SIGNAL_BAND,
    chip_path_for,
    gee_band_name,
    load_calibration_pairs,
    normalize_band_name,
)

SCENE_MANIFEST_PATH = Path("pipeline/data/research/swell_lines/fetch_manifest.json")


def init_gee(project: str | None = None) -> None:
    import ee

    project = project or os.environ.get("GEE_PROJECT")
    if project:
        ee.Initialize(project=project)
    else:
        ee.Initialize()


def write_json(path: Path | str, payload: dict) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def repo_path(path: Path | str) -> str:
    value = Path(path)
    if not value.is_absolute():
        return str(value)
    try:
        return str(value.resolve().relative_to(ROOT))
    except ValueError:
        return str(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch frozen swell-line research chips from GEE.")
    parser.add_argument("--pairs", type=Path, default=CALIBRATION_PAIRS_PATH, help="Calibration pairs JSON.")
    parser.add_argument("--chips-dir", type=Path, default=CHIPS_DIR, help="Output chip directory.")
    parser.add_argument("--band", default=DEFAULT_SIGNAL_BAND, help="Signal band to export, e.g. B04 or B08.")
    parser.add_argument("--project", help="GEE project ID. Defaults to GEE_PROJECT env var.")
    parser.add_argument("--scale", type=int, default=10, help="Export scale in meters. Default: 10.")
    parser.add_argument(
        "--output-manifest",
        type=Path,
        default=SCENE_MANIFEST_PATH,
        help="Optional fetch manifest path.",
    )
    return parser.parse_args()


def _download_geotiff(image, region, destination: Path, scale: int) -> None:
    import requests

    params = {
        "name": destination.stem,
        "bands": image.bandNames().getInfo(),
        "region": region,
        "scale": scale,
        "format": "GEO_TIFF",
    }
    url = image.getDownloadURL(params)
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "zip" in content_type or destination.suffix.lower() == ".zip":
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            tif_members = [name for name in archive.namelist() if name.lower().endswith((".tif", ".tiff"))]
            if not tif_members:
                raise RuntimeError(f"No GeoTIFF found in archive for {destination.name}")
            with archive.open(tif_members[0]) as source:
                destination.write_bytes(source.read())
        return

    destination.write_bytes(response.content)


def _resolve_scene_image(collection, date_str: str):
    import ee

    images = (
        collection.filterDate(date_str, ee.Date(date_str).advance(1, "day"))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    if images.size().getInfo() == 0:
        raise RuntimeError(f"No Sentinel-2 image found for {date_str}")
    return ee.Image(images.first())


def main() -> None:
    args = parse_args()
    import ee

    band = normalize_band_name(args.band)
    source_band = gee_band_name(band)
    pairs = load_calibration_pairs(args.pairs)
    args.chips_dir.mkdir(parents=True, exist_ok=True)
    init_gee(args.project)

    exports: list[dict] = []
    for pair in pairs:
        region = ee.Geometry.Rectangle(pair["window_bbox"])
        collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region)
        for scene_key in ("organized_scene", "flat_scene"):
            scene = pair[scene_key]
            image = _resolve_scene_image(collection, scene["date"]).select([source_band, "SCL"]).toUint16()
            destination = chip_path_for(pair, scene, chips_dir=args.chips_dir, band=band)
            print(f"Fetching {destination.name}")
            _download_geotiff(image.clip(region), pair["window_bbox"], destination, args.scale)
            exports.append(
                {
                    "slug": pair["slug"],
                    "scene_type": scene_key,
                    "date": scene["date"],
                    "band": band,
                    "output_path": repo_path(destination),
                }
            )

    write_json(
        args.output_manifest,
        {
            "pairs_path": repo_path(args.pairs),
            "chips_dir": repo_path(args.chips_dir),
            "band": band,
            "scale_m": args.scale,
            "exports": exports,
        },
    )
    print(json.dumps({"exported": len(exports), "manifest": repo_path(args.output_manifest)}, indent=2))


if __name__ == "__main__":
    main()
