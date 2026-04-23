from __future__ import annotations

from pathlib import Path

from PIL import Image

from pipeline.scripts._gallery_quality import scene_publishability


def test_scene_publishability_rejects_dominant_black_fill(tmp_path: Path) -> None:
    image_path = tmp_path / "mostly-black.png"
    image = Image.new("RGB", (64, 64), color=(0, 0, 0))
    for x in range(8):
        for y in range(64):
            image.putpixel((x, y), (120, 140, 160))
    image.save(image_path)

    publishable, reason, black_ratio = scene_publishability(
        {"rgb_path": str(image_path.relative_to(tmp_path))},
        tmp_path,
    )

    assert publishable is False
    assert reason == "dominant_nodata_fill"
    assert black_ratio is not None and black_ratio > 0.6


def test_scene_publishability_accepts_mostly_real_imagery(tmp_path: Path) -> None:
    image_path = tmp_path / "usable.png"
    image = Image.new("RGB", (64, 64), color=(90, 130, 170))
    for x in range(4):
        for y in range(64):
            image.putpixel((x, y), (0, 0, 0))
    image.save(image_path)

    publishable, reason, black_ratio = scene_publishability(
        {"rgb_path": str(image_path.relative_to(tmp_path))},
        tmp_path,
    )

    assert publishable is True
    assert reason is None
    assert black_ratio is not None and black_ratio < 0.6
