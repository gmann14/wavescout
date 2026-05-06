from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from pipeline.research.swell_lines import chip_filename, chip_path_for, load_calibration_pairs
from pipeline.research.swell_lines.detect import angular_diff_mod180, detect_swell_lines
from pipeline.research.swell_lines.run_experiment import evaluate_pair


def _write_chip(path: Path, signal: np.ndarray, mask: np.ndarray, pixel_size_m: float = 10.0) -> None:
    np.savez(path, signal=signal, mask=mask.astype(np.uint8), pixel_size_m=pixel_size_m)


def _synthetic_wave_chip(
    *,
    azimuth_deg: float,
    wavelength_m: float,
    amplitude: float = 1.0,
    noise_std: float = 0.1,
    shape: tuple[int, int] = (128, 128),
    pixel_size_m: float = 10.0,
) -> tuple[np.ndarray, np.ndarray]:
    rows, cols = shape
    row_grid, col_grid = np.indices(shape)
    x_east_m = (col_grid - cols / 2.0) * pixel_size_m
    y_north_m = -(row_grid - rows / 2.0) * pixel_size_m

    azimuth_rad = math.radians(azimuth_deg)
    east_component = math.sin(azimuth_rad)
    north_component = math.cos(azimuth_rad)
    phase = (x_east_m * east_component + y_north_m * north_component) / wavelength_m
    signal = amplitude * np.sin(2.0 * math.pi * phase)

    rng = np.random.default_rng(7)
    signal += rng.normal(scale=noise_std, size=shape)

    mask = np.zeros(shape, dtype=bool)
    mask[8:-8, 8:-8] = True
    return signal.astype(np.float32), mask


def test_load_calibration_pairs_freezes_expected_scene_set() -> None:
    pairs = load_calibration_pairs()
    frozen_pairs = {(pair["slug"], pair["organized_scene"]["date"], pair["flat_scene"]["date"]) for pair in pairs}

    assert frozen_pairs == {
        ("cow-bay", "2026-03-18", "2022-11-09"),
        ("lawrencetown-beach", "2023-11-19", "2022-11-09"),
        ("hirtles-beach", "2023-09-05", "2024-08-30"),
        ("martinique-beach", "2023-11-19", "2021-10-10"),
    }


def test_chip_path_for_uses_frozen_band_naming() -> None:
    pair = load_calibration_pairs()[0]
    path = chip_path_for(pair, pair["organized_scene"], chips_dir=Path("/tmp/chips"), band="B08")
    assert path == Path("/tmp/chips") / chip_filename("cow-bay", "2026-03-18", "B08")


def test_detect_swell_lines_classifies_organized_synthetic_chip(tmp_path: Path) -> None:
    chip_path = tmp_path / "organized.npz"
    signal, mask = _synthetic_wave_chip(azimuth_deg=32.0, wavelength_m=120.0)
    _write_chip(chip_path, signal, mask)

    result = detect_swell_lines(chip_path)

    assert result.classification == "organized"
    assert result.wavelength_m is not None and abs(result.wavelength_m - 120.0) < 20.0
    assert result.azimuth_deg is not None and angular_diff_mod180(result.azimuth_deg, 32.0) < 12.0


def test_detect_swell_lines_classifies_flat_synthetic_chip(tmp_path: Path) -> None:
    chip_path = tmp_path / "flat.npz"
    rng = np.random.default_rng(11)
    signal = rng.normal(size=(128, 128)).astype(np.float32)
    mask = np.ones((128, 128), dtype=bool)
    mask[:8, :] = False
    mask[-8:, :] = False
    mask[:, :8] = False
    mask[:, -8:] = False
    _write_chip(chip_path, signal, mask)

    result = detect_swell_lines(chip_path)

    assert result.classification == "flat"


def test_evaluate_pair_counts_scene_level_hits_not_pair_hits(tmp_path: Path) -> None:
    organized_chip = tmp_path / "org.npz"
    flat_chip = tmp_path / "flat.npz"
    _write_chip(organized_chip, np.zeros((32, 32), dtype=np.float32), np.ones((32, 32), dtype=bool))
    _write_chip(flat_chip, np.zeros((32, 32), dtype=np.float32), np.ones((32, 32), dtype=bool))

    pair = {
        "pair_id": "demo",
        "slug": "demo",
        "spot_name": "Demo",
        "organized_scene": {
            "date": "2026-01-01",
            "swell_direction_deg": 30,
            "chip_path": str(organized_chip),
        },
        "flat_scene": {
            "date": "2026-01-02",
            "chip_path": str(flat_chip),
        },
    }

    results_by_path = {
        str(organized_chip): {
            "classification": "organized",
            "wavelength_m": 110.0,
            "azimuth_deg": 32.0,
        },
        str(flat_chip): {
            "classification": "flat",
            "wavelength_m": None,
            "azimuth_deg": None,
        },
    }

    class StubResult:
        def __init__(self, payload: dict) -> None:
            self.classification = payload["classification"]
            self.wavelength_m = payload["wavelength_m"]
            self.azimuth_deg = payload["azimuth_deg"]

        def to_dict(self) -> dict:
            return {
                "classification": self.classification,
                "wavelength_m": self.wavelength_m,
                "azimuth_deg": self.azimuth_deg,
            }

    def stub_detector(path: Path, **_: object) -> StubResult:
        return StubResult(results_by_path[str(path)])

    evaluated = evaluate_pair(pair, detector=stub_detector)

    assert evaluated["scenes_correct"] == 2
    assert evaluated["organized_scene"]["passed"] is True
    assert evaluated["flat_scene"]["passed"] is True
