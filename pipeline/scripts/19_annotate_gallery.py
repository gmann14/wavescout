#!/usr/bin/env python3
"""Script 19: Annotate gallery images with break pin overlays.

Reads the gallery manifest and spot configs, overlays break location markers
on satellite images using Pillow, and saves annotated versions alongside
the clean originals.

Usage:
    python3 pipeline/scripts/19_annotate_gallery.py
    python3 pipeline/scripts/19_annotate_gallery.py --spot cow-bay
    python3 pipeline/scripts/19_annotate_gallery.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from _script_utils import get_code_version, now_utc_iso, write_json

ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = ROOT / "pipeline" / "configs"
GALLERY_DIR = ROOT / "pipeline" / "data" / "gallery"
MANIFEST_PATH = GALLERY_DIR / "manifest.json"

# --- Marker style constants ---
MARKER_RADIUS = 6
BORDER_WIDTH = 2
LABEL_OFFSET_X = 10
LABEL_OFFSET_Y = -4
SHADOW_OFFSET = 1
LABEL_PADDING = 3

# Break type -> marker fill color (RGB)
BREAK_COLORS: dict[str, tuple[int, int, int]] = {
    "reef": (0, 200, 180),    # teal
    "point": (255, 165, 0),   # orange
    "beach": (255, 230, 70),  # yellow
}
DEFAULT_COLOR = (0, 200, 180)  # teal fallback
BORDER_COLOR = (255, 255, 255)  # white border
SHADOW_COLOR = (0, 0, 0)       # black shadow for text
LABEL_BG_COLOR = (0, 0, 0, 160)  # semi-transparent black background


def _get_font(size: int = 12) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a readable font, fall back to default."""
    # Try common system fonts
    font_paths = [
        "/System/Library/Fonts/SFCompact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def geo_to_pixel(
    lat: float, lon: float, bbox: list[float], img_width: int, img_height: int
) -> tuple[int, int] | None:
    """Convert geographic coordinates to pixel coordinates.

    Args:
        lat: Latitude of the point.
        lon: Longitude of the point.
        bbox: [west, south, east, north] bounding box.
        img_width: Image width in pixels.
        img_height: Image height in pixels.

    Returns:
        (px_x, px_y) tuple, or None if the point is outside the bbox.
    """
    west, south, east, north = bbox
    bbox_width = east - west
    bbox_height = north - south

    if bbox_width <= 0 or bbox_height <= 0:
        return None

    # Check if point is outside bbox (with small tolerance)
    margin = 0.001  # ~100m tolerance
    if lon < west - margin or lon > east + margin:
        return None
    if lat < south - margin or lat > north + margin:
        return None

    px_x = int((lon - west) / bbox_width * img_width)
    px_y = int((north - lat) / bbox_height * img_height)

    # Clamp to image bounds
    px_x = max(0, min(px_x, img_width - 1))
    px_y = max(0, min(px_y, img_height - 1))

    return (px_x, px_y)


def get_breaks_for_spot(config: dict) -> list[dict]:
    """Get the list of break points for a spot config.

    If the config has a `breaks` array, use that.
    Otherwise, use the single `point` field as the only break.
    """
    if "breaks" in config and config["breaks"]:
        return config["breaks"]

    point = config.get("point", {})
    lat = point.get("lat")
    lon = point.get("lon")
    if lat is not None and lon is not None:
        return [{"name": config.get("name", "Break"), "lat": lat, "lon": lon, "type": "beach"}]

    return []


def annotate_image(
    img_path: str | Path,
    bbox: list[float],
    breaks: list[dict],
) -> Image.Image | None:
    """Annotate an image with break pin markers.

    Args:
        img_path: Path to the source PNG image.
        bbox: [west, south, east, north] bounding box.
        breaks: List of break dicts with name, lat, lon, type.

    Returns:
        Annotated PIL Image, or None if the source can't be opened.
    """
    img_path = Path(img_path)
    if not img_path.exists():
        return None

    try:
        img = Image.open(img_path).convert("RGBA")
    except Exception:
        return None

    img_width, img_height = img.size

    # Create an overlay for semi-transparent elements
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # Also draw on the main image for opaque elements
    draw = ImageDraw.Draw(img)
    font = _get_font(11)

    for brk in breaks:
        lat = brk.get("lat")
        lon = brk.get("lon")
        name = brk.get("name", "")
        break_type = brk.get("type", "beach")

        if lat is None or lon is None:
            continue

        pixel = geo_to_pixel(lat, lon, bbox, img_width, img_height)
        if pixel is None:
            continue

        px_x, px_y = pixel
        fill_color = BREAK_COLORS.get(break_type, DEFAULT_COLOR)

        # Draw white border circle (slightly larger)
        r_outer = MARKER_RADIUS + BORDER_WIDTH
        overlay_draw.ellipse(
            [px_x - r_outer, px_y - r_outer, px_x + r_outer, px_y + r_outer],
            fill=(*BORDER_COLOR, 230),
        )
        # Draw colored fill circle
        overlay_draw.ellipse(
            [px_x - MARKER_RADIUS, px_y - MARKER_RADIUS,
             px_x + MARKER_RADIUS, px_y + MARKER_RADIUS],
            fill=(*fill_color, 255),
        )

        # Draw label if there's a name
        if name:
            label_x = px_x + LABEL_OFFSET_X
            label_y = px_y + LABEL_OFFSET_Y

            # Get text bounding box
            text_bbox = font.getbbox(name)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]

            # Adjust position if label would go off-screen
            if label_x + text_w + LABEL_PADDING * 2 > img_width:
                label_x = px_x - LABEL_OFFSET_X - text_w - LABEL_PADDING * 2
            if label_y < 0:
                label_y = px_y + MARKER_RADIUS + 4

            # Draw semi-transparent background for label
            bg_rect = [
                label_x - LABEL_PADDING,
                label_y - LABEL_PADDING,
                label_x + text_w + LABEL_PADDING,
                label_y + text_h + LABEL_PADDING,
            ]
            overlay_draw.rounded_rectangle(bg_rect, radius=3, fill=LABEL_BG_COLOR)

            # Draw text with shadow for readability
            overlay_draw.text(
                (label_x + SHADOW_OFFSET, label_y + SHADOW_OFFSET),
                name,
                fill=(0, 0, 0, 200),
                font=font,
            )
            overlay_draw.text(
                (label_x, label_y),
                name,
                fill=(255, 255, 255, 255),
                font=font,
            )

    # Composite overlay onto image
    img = Image.alpha_composite(img, overlay)

    # Convert back to RGB for PNG saving
    return img.convert("RGB")


def annotated_path_for(original_path: str | Path) -> Path:
    """Generate the annotated file path from an original path.

    e.g., cow-bay_2022-09-10_1.6m_rgb.png -> cow-bay_2022-09-10_1.6m_rgb_annotated.png
    """
    p = Path(original_path)
    return p.with_name(f"{p.stem}_annotated{p.suffix}")


def process_spot(slug: str, spot_data: dict, configs: dict[str, dict]) -> dict:
    """Annotate all images for a single spot.

    Returns updated spot_data dict with annotated_rgb_path and annotated_nir_path fields.
    """
    config = configs.get(slug)
    if config is None:
        print(f"  WARNING: No config for {slug}, skipping annotation")
        return spot_data

    bbox = config.get("bbox")
    if not bbox:
        print(f"  WARNING: No bbox in config for {slug}")
        return spot_data

    breaks = get_breaks_for_spot(config)
    if not breaks:
        print(f"  WARNING: No break points for {slug}")
        return spot_data

    num_annotated = 0
    for scene in spot_data.get("scenes", []):
        for key, ann_key in [("rgb_path", "annotated_rgb_path"), ("nir_path", "annotated_nir_path")]:
            src_path = scene.get(key)
            if not src_path:
                scene[ann_key] = None
                continue

            # Resolve path (could be relative to ROOT)
            full_src = ROOT / src_path if not Path(src_path).is_absolute() else Path(src_path)
            if not full_src.exists():
                scene[ann_key] = None
                continue

            out_path = annotated_path_for(full_src)
            result = annotate_image(full_src, bbox, breaks)
            if result is not None:
                result.save(out_path, "PNG", optimize=True)
                # Store path relative to ROOT (same convention as rgb_path)
                scene[ann_key] = str(out_path.relative_to(ROOT))
                num_annotated += 1
            else:
                scene[ann_key] = None

    print(f"  {slug}: {num_annotated} annotated images ({len(breaks)} breaks)")
    return spot_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate gallery images with break pins")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--spot", help="Annotate a single spot by slug")
    group.add_argument("--all", action="store_true", help="Annotate all spots in the gallery manifest")
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        print(f"ERROR: Gallery manifest not found at {MANIFEST_PATH}")
        print("Run 16_generate_gallery_fast.py first.")
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    # Load all spot configs
    configs: dict[str, dict] = {}
    for config_path in CONFIGS_DIR.glob("*.json"):
        try:
            with open(config_path) as f:
                config = json.load(f)
            configs[config_path.stem] = config
        except (json.JSONDecodeError, IOError):
            continue

    print("Break Pin Annotator")
    print(f"  Manifest: {MANIFEST_PATH}")
    print(f"  Configs: {len(configs)} loaded")
    print()

    spots_to_process = manifest.get("spots", [])
    if args.spot:
        spots_to_process = [s for s in spots_to_process if s.get("slug") == args.spot]
        if not spots_to_process:
            print(f"ERROR: Spot '{args.spot}' not found in gallery manifest")
            sys.exit(1)

    total_annotated = 0
    for spot_data in spots_to_process:
        slug = spot_data.get("slug", "unknown")
        spot_data = process_spot(slug, spot_data, configs)
        total_annotated += sum(
            (1 if s.get("annotated_rgb_path") else 0) + (1 if s.get("annotated_nir_path") else 0)
            for s in spot_data.get("scenes", [])
        )

    # Write updated manifest
    manifest["annotation"] = {
        "annotated_at_utc": now_utc_iso(),
        "code_version": get_code_version(),
        "total_annotated_images": total_annotated,
    }
    write_json(MANIFEST_PATH, manifest)

    print(f"\nDone! {total_annotated} annotated images generated.")
    print(f"Manifest updated: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
