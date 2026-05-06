from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from pipeline.research.swell_lines.detect import angular_diff_mod180
from pipeline.research.swell_lines_v3.detect import (
    build_offshore_corridor_mask,
    detect_swell_lines_v3,
    load_spot_context,
)
from pipeline.research.swell_lines_v3.run_experiment import evaluate_pair


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

    rng = np.random.default_rng(23)
    signal += rng.normal(scale=noise_std, size=shape)

    mask = np.zeros(shape, dtype=bool)
    mask[8:-8, 8:-8] = True
    return signal.astype(np.float32), mask


def test_load_spot_context_uses_repo_geometry() -> None:
    context = load_spot_context("lawrencetown-beach")

    assert context.slug == "lawrencetown-beach"
    assert context.segment_id == "ns-seg-03842"
    assert abs(context.segment_orientation_deg - 196.7) < 0.2


def test_load_spot_context_falls_back_to_best_scored_nearby_segment() -> None:
    context = load_spot_context("hirtles-beach")

    assert context.slug == "hirtles-beach"
    assert context.segment_id == "ns-seg-01506"
    assert abs(context.segment_orientation_deg - 148.9) < 0.2


def test_build_offshore_corridor_mask_selects_seaward_strip() -> None:
    mask = build_offshore_corridor_mask(
        shape=(100, 100),
        anchor_row=50.0,
        anchor_col=50.0,
        orientation_deg=0.0,
        pixel_size_m=10.0,
        near_m=20.0,
        far_m=200.0,
        alongshore_half_width_m=40.0,
    )

    assert mask[48, 50]
    assert mask[40, 50]
    assert not mask[52, 50]
    assert not mask[40, 60]


def test_detect_swell_lines_v3_classifies_organized_synthetic_chip(tmp_path: Path) -> None:
    chip_path = tmp_path / "organized.npz"
    signal, mask = _synthetic_wave_chip(azimuth_deg=32.0, wavelength_m=120.0)
    _write_chip(chip_path, signal, mask)

    result = detect_swell_lines_v3(
        chip_path,
        anchor_row=64.0,
        anchor_col=64.0,
        segment_orientation_deg=32.0,
        corridor_near_m=0.0,
        corridor_far_m=1200.0,
        corridor_half_width_m=700.0,
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
    assert result.azimuth_delta_vs_segment_deg is not None and result.azimuth_delta_vs_segment_deg < 10.0


def test_evaluate_pair_v3_counts_scene_level_hits_not_pair_hits(tmp_path: Path) -> None:
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
        def __init__(self, classification: str, cluster_wavelength_m: float | None, cluster_azimuth_deg: float | None, azimuth_delta_vs_segment_deg: float | None) -> None:
            self.classification = classification
            self.cluster_wavelength_m = cluster_wavelength_m
            self.cluster_azimuth_deg = cluster_azimuth_deg
            self.azimuth_delta_vs_segment_deg = azimuth_delta_vs_segment_deg

        def to_dict(self) -> dict:
            return {
                "classification": self.classification,
                "cluster_wavelength_m": self.cluster_wavelength_m,
                "cluster_azimuth_deg": self.cluster_azimuth_deg,
                "azimuth_delta_vs_segment_deg": self.azimuth_delta_vs_segment_deg,
            }

    def stub_detector(path: Path, **_: object) -> StubResult:
        if path == organized_chip:
            return StubResult("organized", 115.0, 28.0, 5.0)
        return StubResult("flat", None, None, None)

    evaluated = evaluate_pair(pair, detector=stub_detector)

    assert evaluated["scenes_correct"] == 2
    assert evaluated["organized_scene"]["passed"] is True
    assert evaluated["flat_scene"]["passed"] is True
