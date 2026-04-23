from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

SCENE_BLACK_RATIO_MAX = 0.6


def scene_black_ratio_from_path(path: Path) -> float | None:
    if not path.exists():
        return None

    with Image.open(path) as image:
        thumb = image.convert("RGB").resize((64, 64))
        pixels = [
            thumb.getpixel((x, y))
            for y in range(thumb.height)
            for x in range(thumb.width)
        ]

    if not pixels:
        return None

    black = sum(1 for r, g, b in pixels if r < 8 and g < 8 and b < 8)
    return black / len(pixels)


def scene_publishability(scene: dict[str, Any], root: Path) -> tuple[bool, str | None, float | None]:
    rgb_path = scene.get("rgb_path")
    if not rgb_path:
        return False, "missing_rgb", None

    black_ratio = scene_black_ratio_from_path(root / rgb_path)
    if black_ratio is None:
        return False, "missing_rgb", None
    if black_ratio > SCENE_BLACK_RATIO_MAX:
        return False, "dominant_nodata_fill", black_ratio
    return True, None, black_ratio

