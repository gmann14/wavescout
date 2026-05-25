"""Fixture-backed tests for bathymetry sampling and scoring.

GEBCO datasets are large and not committed. These tests stand in for
the real loader with a tiny duck-typed object that exposes the same
``variables`` shape (``lat``, ``lon``, ``elevation``).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from pipeline.scripts._bathymetry import (
    MAX_BATHY_SCORE,
    sample_bathymetry_transect,
    score_bathymetry,
    score_from_depth_samples,
    try_load_gebco,
)


@dataclass
class FakeGebco:
    """In-memory stand-in for a netCDF4.Dataset."""

    variables: dict


def _grid(lats: np.ndarray, lons: np.ndarray, elev_fn) -> FakeGebco:
    elevation = np.zeros((lats.size, lons.size), dtype=float)
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            elevation[i, j] = elev_fn(lon, lat)
    return FakeGebco(
        variables={
            "lat": lats,
            "lon": lons,
            "elevation": elevation,
        }
    )


def test_missing_bathymetry_returns_zero() -> None:
    score, explanation = score_bathymetry(-64.0, 44.0, None)
    assert score == 0.0
    assert "not available" in explanation.lower()


def test_synthetic_steep_gradient_scores_above_flat_shelf() -> None:
    lats = np.linspace(43.95, 44.05, 21)
    lons = np.linspace(-64.05, -63.95, 21)

    # Steep south-facing transect: depth grows quickly as latitude
    # decreases (i.e. as we move south, offshore).
    def steep(lon: float, lat: float) -> float:
        depth_m = max(0.0, (44.00 - lat) * 600.0)
        return -depth_m

    # Flat shelf: depth barely changes.
    def flat(lon: float, lat: float) -> float:
        depth_m = max(0.0, (44.00 - lat) * 5.0)
        return -depth_m

    steep_ds = _grid(lats, lons, steep)
    flat_ds = _grid(lats, lons, flat)

    steep_score, steep_expl = score_bathymetry(
        -64.00, 44.00, steep_ds, offshore_bearing_deg=180.0
    )
    flat_score, flat_expl = score_bathymetry(
        -64.00, 44.00, flat_ds, offshore_bearing_deg=180.0
    )

    assert steep_score > flat_score
    assert steep_score <= MAX_BATHY_SCORE
    assert flat_score >= 0.0
    assert "steep" in steep_expl.lower() or "moderate" in steep_expl.lower()
    assert "gradual" in flat_expl.lower()


def test_bathymetry_lookup_failure_is_controlled() -> None:
    class Broken:
        variables = {}

    score, explanation = score_bathymetry(
        -64.0, 44.0, Broken(), offshore_bearing_deg=180.0
    )
    assert score == 0.0
    assert "unavailable" in explanation.lower() or "failed" in explanation.lower()


def test_bathymetry_sampling_uses_offshore_bearing() -> None:
    """A south-facing segment should deepen southward, not northward."""
    lats = np.linspace(43.95, 44.05, 51)
    lons = np.linspace(-64.05, -63.95, 51)

    # Depth is deeper at low latitudes (offshore = south).
    def south_deepens(lon: float, lat: float) -> float:
        return -max(0.0, (44.00 - lat) * 800.0)

    ds = _grid(lats, lons, south_deepens)

    south_samples = sample_bathymetry_transect(
        ds, -64.00, 44.00, offshore_bearing_deg=180.0,
        distances_m=(0.0, 500.0, 1000.0),
    )
    north_samples = sample_bathymetry_transect(
        ds, -64.00, 44.00, offshore_bearing_deg=0.0,
        distances_m=(0.0, 500.0, 1000.0),
    )

    south_score, _ = score_from_depth_samples(south_samples, distances_m=(0.0, 500.0, 1000.0))
    north_score, _ = score_from_depth_samples(north_samples, distances_m=(0.0, 500.0, 1000.0))

    # Southward bearing should pick up the deepening transect; northward
    # bearing samples shallower or land cells and should score lower.
    assert south_score > north_score


def test_try_load_gebco_returns_none_when_file_missing(tmp_path: Path) -> None:
    assert try_load_gebco(tmp_path / "missing.nc") is None


def test_score_from_depth_samples_handles_single_valid_sample() -> None:
    score, explanation = score_from_depth_samples([5.0, None, None])
    assert score == 0.0
    assert "unavailable" in explanation.lower()


def test_score_from_depth_samples_returns_zero_for_uphill_gradient() -> None:
    # If depth decreases offshore (uphill), this is not surf-favorable.
    score, explanation = score_from_depth_samples([20.0, 10.0, 5.0])
    assert score == 0.0
    assert "non-deepening" in explanation.lower()
