from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from pipeline.research.swell_lines import chip_filename, chip_path_for, load_calibration_pairs
from pipeline.research.swell_lines.detect import angular_diff_mod180
from pipeline.research.swell_lines_v2.detect import (
    TileVote,
    cluster_tile_votes,
    detect_swell_lines_v2,
    extract_tiles,
)
from pipeline.research.swell_lines_v2.run_experiment import evaluate_pair


def _write_chip(path: Path, signal: np.ndarray, mask: np.ndarray, pixel_size_m: float = 10.0) -> None:
    np.savez(path, signal=signal, mask=mask.astype(np.uint8), pixel_size_m=pixel_size_m)


def _synthetic_wave_chip(
    *,
    azimuth_deg: float,
    wavelength_m: float,
    amplitude: float = 1.0,
    noise_std: float = 0.05,
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

    rng = np.random.default_rng(17)
    signal += rng.normal(scale=noise_std, size=shape)

    mask = np.zeros(shape, dtype=bool)
    mask[8:-8, 8:-8] = True
    return signal.astype(np.float32), mask


def test_chip_path_for_keeps_frozen_b04_naming() -> None:
    pair = load_calibration_pairs()[0]
    path = chip_path_for(pair, pair["organized_scene"], chips_dir=Path("/tmp/chips"), band="B04")
    assert path == Path("/tmp/chips") / chip_filename("cow-bay", "2026-03-18", "B04")


def test_extract_tiles_filters_invalid_windows() -> None:
    signal = np.arange(100, dtype=float).reshape(10, 10)
    valid_mask = np.ones((10, 10), dtype=bool)
    valid_mask[:3, :3] = False

    tiles = extract_tiles(
        signal,
        valid_mask,
        window_height_px=4,
        window_width_px=4,
        stride_px=2,
        min_valid_fraction=0.75,
    )

    starts = {(tile.row_start, tile.col_start) for tile in tiles}
    assert (0, 0) not in starts
    assert (0, 2) in starts
    assert (2, 2) in starts


def test_detect_swell_lines_v2_classifies_organized_synthetic_chip(tmp_path: Path) -> None:
    chip_path = tmp_path / "organized.npz"
    signal, mask = _synthetic_wave_chip(azimuth_deg=32.0, wavelength_m=120.0)
    _write_chip(chip_path, signal, mask)

    result = detect_swell_lines_v2(
        chip_path,
        window_height_m=640.0,
        window_width_m=640.0,
        stride_m=160.0,
        min_cluster_share=0.45,
        min_cluster_tile_count=3,
    )

    assert result.classification == "organized"
    assert result.cluster_wavelength_m is not None and abs(result.cluster_wavelength_m - 120.0) < 20.0
    assert result.cluster_azimuth_deg is not None
    assert angular_diff_mod180(result.cluster_azimuth_deg, 32.0) < 10.0


def test_cluster_tile_votes_rejects_disagreeing_tiles() -> None:
    votes = [
        TileVote(row_start=0, col_start=0, row_stop=8, col_stop=8, valid_fraction=1.0, azimuth_deg=0.0, wavelength_m=120.0, coherence=12.0, peak_fraction=0.2),
        TileVote(row_start=0, col_start=8, row_stop=8, col_stop=16, valid_fraction=1.0, azimuth_deg=45.0, wavelength_m=118.0, coherence=11.0, peak_fraction=0.2),
        TileVote(row_start=8, col_start=0, row_stop=16, col_stop=8, valid_fraction=1.0, azimuth_deg=90.0, wavelength_m=122.0, coherence=10.0, peak_fraction=0.2),
        TileVote(row_start=8, col_start=8, row_stop=16, col_stop=16, valid_fraction=1.0, azimuth_deg=135.0, wavelength_m=121.0, coherence=9.5, peak_fraction=0.2),
    ]

    summary = cluster_tile_votes(votes, angle_bin_deg=15.0, min_cluster_share=0.5, min_cluster_tile_count=3)

    assert summary.classification == "flat"
    assert summary.dominant_cluster_share == 0.25


def test_evaluate_pair_v2_counts_scene_level_hits_not_pair_hits(tmp_path: Path) -> None:
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

    class StubResult:
        def __init__(self, classification: str, cluster_wavelength_m: float | None, cluster_azimuth_deg: float | None) -> None:
            self.classification = classification
            self.cluster_wavelength_m = cluster_wavelength_m
            self.cluster_azimuth_deg = cluster_azimuth_deg

        def to_dict(self) -> dict:
            return {
                "classification": self.classification,
                "cluster_wavelength_m": self.cluster_wavelength_m,
                "cluster_azimuth_deg": self.cluster_azimuth_deg,
            }

    def stub_detector(path: Path, **_: object) -> StubResult:
        if path == organized_chip:
            return StubResult("organized", 115.0, 28.0)
        return StubResult("flat", None, None)

    evaluated = evaluate_pair(pair, detector=stub_detector)

    assert evaluated["scenes_correct"] == 2
    assert evaluated["organized_scene"]["passed"] is True
    assert evaluated["flat_scene"]["passed"] is True
