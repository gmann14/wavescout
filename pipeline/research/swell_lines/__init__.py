from __future__ import annotations

import json
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parent
CALIBRATION_PAIRS_PATH = RESEARCH_DIR / "calibration_pairs.json"
RESULTS_PATH = RESEARCH_DIR / "results.json"
REPORT_PATH = RESEARCH_DIR / "REPORT.md"
CHIPS_DIR = Path("pipeline/data/research/swell_lines/chips")
DEFAULT_SIGNAL_BAND = "B04"
WATER_SCL_VALUE = 6


def normalize_band_name(band: str) -> str:
    band = band.upper()
    if band == "SCL":
        return band
    if not band.startswith("B"):
        band = f"B{band}"
    return band


def gee_band_name(band: str) -> str:
    normalized = normalize_band_name(band)
    if normalized == "SCL":
        return normalized
    prefix, digits = normalized[0], normalized[1:]
    try:
        return f"{prefix}{int(digits)}"
    except ValueError:
        return normalized


def chip_filename(slug: str, date: str, band: str = DEFAULT_SIGNAL_BAND) -> str:
    normalized_band = normalize_band_name(band).lower()
    return f"{slug}_{date}_{normalized_band}.tif"


def chip_path_for(
    spot: dict | str,
    scene: dict,
    chips_dir: Path | str = CHIPS_DIR,
    band: str = DEFAULT_SIGNAL_BAND,
) -> Path:
    if scene.get("chip_path"):
        return Path(scene["chip_path"])
    slug = spot["slug"] if isinstance(spot, dict) else str(spot)
    filename = scene.get("chip_filename") or chip_filename(slug, scene["date"], band)
    return Path(chips_dir) / filename


def load_calibration_pairs(path: Path | str = CALIBRATION_PAIRS_PATH) -> list[dict]:
    with Path(path).open() as handle:
        payload = json.load(handle)

    pairs = payload.get("pairs", [])
    for pair in pairs:
        pair.setdefault("pair_id", pair["slug"])
        for scene_key in ("organized_scene", "flat_scene"):
            scene = pair[scene_key]
            scene.setdefault("scene_id", f"{pair['slug']}_{scene['date']}")
    return pairs
