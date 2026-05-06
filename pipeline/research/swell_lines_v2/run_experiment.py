#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

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
from pipeline.research.swell_lines.detect import angular_diff_mod180, load_chip  # noqa: E402
from pipeline.research.swell_lines_v2 import (  # noqa: E402
    DEFAULT_PRESET_NAME,
    PLOTS_DIR,
    REPORT_PATH,
    RESULTS_PATH,
    WINDOW_PRESETS,
)
from pipeline.research.swell_lines_v2.detect import detect_swell_lines_v2  # noqa: E402

try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
except ImportError:  # pragma: no cover - optional runtime dependency
    plt = None
    Rectangle = None


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
    parser = argparse.ArgumentParser(description="Run the localized swell-line v2 experiment.")
    parser.add_argument("--pairs", type=Path, default=CALIBRATION_PAIRS_PATH, help="Calibration pairs JSON.")
    parser.add_argument("--chips-dir", type=Path, default=CHIPS_DIR, help="Directory containing fetched chips.")
    parser.add_argument("--band", default=DEFAULT_SIGNAL_BAND, help="Signal band to read, e.g. B04.")
    parser.add_argument("--output", type=Path, default=RESULTS_PATH, help="Results JSON output path.")
    parser.add_argument(
        "--preset",
        choices=sorted(WINDOW_PRESETS),
        default=DEFAULT_PRESET_NAME,
        help="Window geometry preset.",
    )
    parser.add_argument("--window-height-m", type=float, help="Optional window height override.")
    parser.add_argument("--window-width-m", type=float, help="Optional window width override.")
    parser.add_argument("--stride-m", type=float, help="Optional stride override.")
    parser.add_argument("--min-local-coherence", type=float, default=4.0, help="Minimum coherence for a retained tile.")
    parser.add_argument(
        "--min-local-peak-fraction",
        type=float,
        default=0.1,
        help="Minimum spectral peak fraction for a retained tile.",
    )
    parser.add_argument("--min-cluster-share", type=float, default=0.5, help="Minimum share for the dominant azimuth cluster.")
    parser.add_argument("--min-cluster-tile-count", type=int, default=3, help="Minimum tile count for the dominant cluster.")
    parser.add_argument(
        "--min-cluster-median-coherence",
        type=float,
        default=4.0,
        help="Minimum median coherence inside the dominant cluster.",
    )
    parser.add_argument("--theta-step-deg", type=float, default=2.0, help="Radon angle step in degrees.")
    parser.add_argument("--plots-dir", type=Path, default=PLOTS_DIR, help="Directory for optional diagnostic plots.")
    parser.add_argument("--write-plots", action="store_true", help="Write per-scene diagnostic plots if matplotlib is available.")
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
    }


def _flat_scene_pass(result) -> tuple[bool, dict]:
    passed = result.classification == "flat"
    return passed, {"classification_ok": passed}


def evaluate_pair(
    pair: dict,
    *,
    band: str = DEFAULT_SIGNAL_BAND,
    chips_dir: Path | str = CHIPS_DIR,
    detector=detect_swell_lines_v2,
    detector_kwargs: dict | None = None,
) -> dict:
    detector_kwargs = detector_kwargs or {}
    organized_scene = pair["organized_scene"]
    flat_scene = pair["flat_scene"]

    organized_chip = chip_path_for(pair, organized_scene, chips_dir=chips_dir, band=band)
    flat_chip = chip_path_for(pair, flat_scene, chips_dir=chips_dir, band=band)
    organized_result = detector(organized_chip, **detector_kwargs)
    flat_result = detector(flat_chip, **detector_kwargs)

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


def _render_scene_plot(scene_label: str, chip_path: Path, result: dict, output_path: Path) -> None:
    if plt is None or Rectangle is None:  # pragma: no cover - runtime dependency
        return

    signal, mask, _ = load_chip(chip_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    figure, (image_ax, hist_ax) = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    image_ax.imshow(signal, cmap="gray")
    image_ax.set_title(
        f"{scene_label}\n{result['classification']} | share={result['dominant_cluster_share']:.2f} | "
        f"az={result['cluster_azimuth_deg']!s} | wl={result['cluster_wavelength_m']!s}"
    )
    image_ax.set_axis_off()

    if mask is not None:
        masked = np.ma.masked_where(mask.astype(bool), np.ones_like(mask))
        image_ax.imshow(masked, cmap="Reds", alpha=0.15)

    for vote in result.get("tile_votes", []):
        color = plt.cm.hsv((vote["azimuth_deg"] % 180.0) / 180.0)
        patch = Rectangle(
            (vote["col_start"], vote["row_start"]),
            vote["col_stop"] - vote["col_start"],
            vote["row_stop"] - vote["row_start"],
            fill=False,
            edgecolor=color,
            linewidth=1.25,
            alpha=0.7,
        )
        image_ax.add_patch(patch)

    histogram = result.get("cluster_histogram", {})
    labels = list(histogram)
    counts = [histogram[label] for label in labels]
    hist_ax.bar(labels, counts, color="#385170")
    hist_ax.set_title("Azimuth Cluster Counts")
    hist_ax.set_xlabel("Bin center (deg)")
    hist_ax.set_ylabel("Tiles")
    hist_ax.tick_params(axis="x", rotation=45)

    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def run_experiment(
    *,
    pairs_path: Path | str = CALIBRATION_PAIRS_PATH,
    chips_dir: Path | str = CHIPS_DIR,
    band: str = DEFAULT_SIGNAL_BAND,
    output_path: Path | str = RESULTS_PATH,
    detector_kwargs: dict | None = None,
    plots_dir: Path | str = PLOTS_DIR,
    write_plots: bool = False,
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
        "preset": detector_kwargs.get("preset_name", DEFAULT_PRESET_NAME),
        "detector_kwargs": detector_kwargs,
        "pairs": pair_results,
        "report_path": repo_path(REPORT_PATH),
    }
    write_json(output_path, payload)

    if write_plots:
        plot_root = Path(plots_dir)
        for pair_result in pair_results:
            for scene_key in ("organized_scene", "flat_scene"):
                scene_result = pair_result[scene_key]
                output_name = f"{pair_result['slug']}_{scene_result['date']}_{scene_key}.png"
                _render_scene_plot(
                    f"{pair_result['slug']} {scene_key}",
                    Path(scene_result["chip_path"]),
                    scene_result["result"],
                    plot_root / output_name,
                )

    return payload


def main() -> None:
    args = parse_args()
    detector_kwargs = {
        "preset_name": args.preset,
        "window_height_m": args.window_height_m,
        "window_width_m": args.window_width_m,
        "stride_m": args.stride_m,
        "min_local_coherence": args.min_local_coherence,
        "min_local_peak_fraction": args.min_local_peak_fraction,
        "min_cluster_share": args.min_cluster_share,
        "min_cluster_tile_count": args.min_cluster_tile_count,
        "min_cluster_median_coherence": args.min_cluster_median_coherence,
        "theta_step_deg": args.theta_step_deg,
    }
    payload = run_experiment(
        pairs_path=args.pairs,
        chips_dir=args.chips_dir,
        band=args.band,
        output_path=args.output,
        detector_kwargs=detector_kwargs,
        plots_dir=args.plots_dir,
        write_plots=args.write_plots,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "scenes_correct": payload["scenes_correct"],
                "scene_count": payload["scene_count"],
                "preset": payload["preset"],
            },
            indent=2,
        )
    )
    if args.strict and payload["scenes_correct"] < payload["threshold"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
