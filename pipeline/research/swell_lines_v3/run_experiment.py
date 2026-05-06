#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.research.swell_lines import (  # noqa: E402
    CALIBRATION_PAIRS_PATH,
    CHIPS_DIR,
    DEFAULT_SIGNAL_BAND,
    chip_path_for,
    load_calibration_pairs,
    normalize_band_name,
)
from pipeline.research.swell_lines.detect import angular_diff_mod180  # noqa: E402
from pipeline.research.swell_lines_v3 import REPORT_PATH, RESULTS_PATH  # noqa: E402
from pipeline.research.swell_lines_v3.detect import detect_swell_lines_v3  # noqa: E402


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_code_version() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode == 0:
        return result.stdout.strip()
    return None


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
    parser = argparse.ArgumentParser(description="Run the v3 corridor-masked swell-line experiment.")
    parser.add_argument("--pairs", type=Path, default=CALIBRATION_PAIRS_PATH, help="Calibration pairs JSON.")
    parser.add_argument("--chips-dir", type=Path, default=CHIPS_DIR, help="Directory containing fetched chips.")
    parser.add_argument("--band", default=DEFAULT_SIGNAL_BAND, help="Signal band to read, e.g. B04.")
    parser.add_argument("--output", type=Path, default=RESULTS_PATH, help="Results JSON output path.")
    parser.add_argument("--corridor-near-m", type=float, default=250.0, help="Near edge of the offshore corridor.")
    parser.add_argument("--corridor-far-m", type=float, default=1750.0, help="Far edge of the offshore corridor.")
    parser.add_argument(
        "--corridor-half-width-m",
        type=float,
        default=900.0,
        help="Half-width of the offshore corridor measured alongshore.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if the experiment misses the 6/8 bar.")
    return parser.parse_args()


def _organized_scene_pass(scene: dict, result) -> tuple[bool, dict]:
    wavelength_ok = result.cluster_wavelength_m is not None and 80.0 <= result.cluster_wavelength_m <= 250.0
    azimuth_delta = angular_diff_mod180(result.cluster_azimuth_deg, scene.get("swell_direction_deg"))
    azimuth_ok = azimuth_delta is not None and azimuth_delta <= 25.0
    classification_ok = result.classification == "organized"
    passed = bool(wavelength_ok and azimuth_ok and classification_ok)
    return passed, {
        "classification_ok": classification_ok,
        "wavelength_ok": wavelength_ok,
        "azimuth_ok": azimuth_ok,
        "azimuth_delta_deg": azimuth_delta,
        "azimuth_delta_vs_segment_deg": result.azimuth_delta_vs_segment_deg,
    }


def _flat_scene_pass(result) -> tuple[bool, dict]:
    passed = result.classification == "flat"
    return passed, {
        "classification_ok": passed,
        "azimuth_delta_vs_segment_deg": result.azimuth_delta_vs_segment_deg,
    }


def evaluate_pair(
    pair: dict,
    *,
    band: str = DEFAULT_SIGNAL_BAND,
    chips_dir: Path | str = CHIPS_DIR,
    detector=detect_swell_lines_v3,
    detector_kwargs: dict | None = None,
) -> dict:
    detector_kwargs = detector_kwargs or {}
    organized_scene = pair["organized_scene"]
    flat_scene = pair["flat_scene"]

    organized_chip = chip_path_for(pair, organized_scene, chips_dir=chips_dir, band=band)
    flat_chip = chip_path_for(pair, flat_scene, chips_dir=chips_dir, band=band)
    organized_result = detector(organized_chip, spot_slug=pair["slug"], **detector_kwargs)
    flat_result = detector(flat_chip, spot_slug=pair["slug"], **detector_kwargs)

    organized_passed, organized_checks = _organized_scene_pass(organized_scene, organized_result)
    flat_passed, flat_checks = _flat_scene_pass(flat_result)

    return {
        "pair_id": pair["pair_id"],
        "slug": pair["slug"],
        "spot_name": pair["spot_name"],
        "organized_scene": {
            **organized_scene,
            "chip_path": str(organized_chip),
            "result": organized_result.to_dict(),
            "checks": organized_checks,
            "passed": organized_passed,
        },
        "flat_scene": {
            **flat_scene,
            "chip_path": str(flat_chip),
            "result": flat_result.to_dict(),
            "checks": flat_checks,
            "passed": flat_passed,
        },
        "scenes_correct": int(organized_passed) + int(flat_passed),
    }


def run_experiment(
    *,
    pairs_path: Path | str = CALIBRATION_PAIRS_PATH,
    chips_dir: Path | str = CHIPS_DIR,
    band: str = DEFAULT_SIGNAL_BAND,
    output_path: Path | str = RESULTS_PATH,
    detector_kwargs: dict | None = None,
) -> dict:
    pairs = load_calibration_pairs(pairs_path)
    normalized_band = normalize_band_name(band)
    detector_kwargs = detector_kwargs or {}

    pair_results = [
        evaluate_pair(
            pair,
            band=normalized_band,
            chips_dir=chips_dir,
            detector_kwargs=detector_kwargs,
        )
        for pair in pairs
    ]
    scenes_correct = sum(item["scenes_correct"] for item in pair_results)
    scene_count = len(pair_results) * 2
    status = "pass" if scenes_correct >= 6 else "fail"
    payload = {
        "generated_at_utc": now_utc_iso(),
        "code_version": get_code_version(),
        "pairs_path": repo_path(pairs_path),
        "chips_dir": repo_path(chips_dir),
        "band": normalized_band,
        "scene_count": scene_count,
        "scenes_correct": scenes_correct,
        "threshold": 6,
        "status": status,
        "detector_kwargs": detector_kwargs,
        "pairs": pair_results,
        "report_path": repo_path(REPORT_PATH),
    }
    write_json(output_path, payload)
    return payload


def main() -> None:
    args = parse_args()
    payload = run_experiment(
        pairs_path=args.pairs,
        chips_dir=args.chips_dir,
        band=args.band,
        output_path=args.output,
        detector_kwargs={
            "corridor_near_m": args.corridor_near_m,
            "corridor_far_m": args.corridor_far_m,
            "corridor_half_width_m": args.corridor_half_width_m,
        },
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "scenes_correct": payload["scenes_correct"],
                "scene_count": payload["scene_count"],
            },
            indent=2,
        )
    )
    if args.strict and payload["scenes_correct"] < payload["threshold"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
