#!/usr/bin/env python3
"""Build atlas static data for the web viewer.

Copies atlas section GeoJSON and gallery data to web/public/data/atlas/.
Run after scripts 17 (tiling) and optionally 18 (gallery generation).

Usage:
    python3 pipeline/scripts/build_atlas_web_data.py
"""

import json
import shutil
from pathlib import Path

from _public_dataset import (
    gallery_url_prefix_from_env,
    public_gallery_url,
    validate_public_dataset,
    write_dataset_manifest,
)

ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE_DATA = ROOT / "pipeline" / "data"
ATLAS_DATA = PIPELINE_DATA / "atlas"
ATLAS_GALLERY_SRC = ATLAS_DATA / "gallery"
WEB_ATLAS = ROOT / "web" / "public" / "data" / "atlas"
WEB_ATLAS_GALLERY = ROOT / "web" / "public" / "atlas-gallery"


def build_sections() -> None:
    """Copy atlas sections GeoJSON to web, optimized for size."""
    src = ATLAS_DATA / "ns_atlas_sections.geojson"
    if not src.exists():
        print("  sections: no atlas data found. Run script 17 first.")
        return

    with open(src) as f:
        data = json.load(f)

    for feature in data.get("features", []):
        feature.setdefault("properties", {})
        feature["properties"]["publication_status"] = "public_coarse"

    out = WEB_ATLAS / "sections.json"
    with open(out, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    size_kb = out.stat().st_size / 1024
    print(f"  sections.json: {len(data['features'])} sections, {size_kb:.1f}KB")


def build_gallery(gallery_url_prefix: str | None = None) -> None:
    """Copy atlas gallery manifest and images to web.

    When ``gallery_url_prefix`` is provided, emitted image paths use
    absolute https URLs under that prefix while images still land under
    ``web/public/atlas-gallery/``.
    """
    manifest_src = ATLAS_GALLERY_SRC / "manifest.json"
    if not manifest_src.exists():
        # Write empty manifest so the web app doesn't 404
        empty = {"sections": []}
        out = WEB_ATLAS / "gallery.json"
        with open(out, "w") as f:
            json.dump(empty, f, separators=(",", ":"))
        print("  gallery.json: no gallery data (empty manifest written)")
        return

    with open(manifest_src) as f:
        manifest = json.load(f)

    # Copy images and update paths
    for section in manifest.get("sections", []):
        slug = section["slug"]
        section["publication_status"] = "public_coarse"
        section_gallery_dir = WEB_ATLAS_GALLERY / slug
        section_gallery_dir.mkdir(parents=True, exist_ok=True)

        for scene in section.get("scenes", []):
            scene["scene_id"] = f"{slug}:{scene['date']}"
            quality_score = scene.get("quality_score")
            if quality_score is None:
                scene["quality_status"] = "degraded"
            elif quality_score >= 90:
                scene["quality_status"] = "usable"
            elif quality_score >= 60:
                scene["quality_status"] = "degraded"
            else:
                scene["quality_status"] = "rejected"
            for key in ("rgb_path", "nir_path"):
                src_path_str = scene.get(key)
                if not src_path_str:
                    continue
                src_path = ROOT / src_path_str
                if src_path.exists():
                    dst = section_gallery_dir / src_path.name
                    shutil.copy2(src_path, dst)
                    web_relative = f"/atlas-gallery/{slug}/{src_path.name}"
                    scene[key] = public_gallery_url(
                        web_relative, prefix=gallery_url_prefix
                    )
                else:
                    scene[key] = None

    out = WEB_ATLAS / "gallery.json"
    with open(out, "w") as f:
        json.dump(manifest, f, separators=(",", ":"))

    total_sections = len(manifest.get("sections", []))
    total_images = sum(
        (1 if s.get("rgb_path") else 0) + (1 if s.get("nir_path") else 0)
        for sec in manifest.get("sections", [])
        for s in sec.get("scenes", [])
    )
    size_kb = out.stat().st_size / 1024
    print(f"  gallery.json: {total_sections} sections, {total_images} images, {size_kb:.1f}KB")


def main() -> None:
    WEB_ATLAS.mkdir(parents=True, exist_ok=True)
    WEB_ATLAS_GALLERY.mkdir(parents=True, exist_ok=True)

    gallery_url_prefix = gallery_url_prefix_from_env()

    print("Building atlas web data...")
    if gallery_url_prefix:
        print(f"  gallery URL prefix: {gallery_url_prefix}")
    build_sections()
    build_gallery(gallery_url_prefix=gallery_url_prefix)
    manifest_path = write_dataset_manifest(gallery_url_prefix=gallery_url_prefix)
    validate_public_dataset(strict=False, require_atlas=True)
    print(f"  dataset-manifest.json: {manifest_path.stat().st_size / 1024:.1f}KB")
    print("Done!")


if __name__ == "__main__":
    main()
