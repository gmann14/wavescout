"""Bathymetry helpers split out of `11_score_geometry.py` for testability.

This module intentionally has no hard dependency on `netCDF4` or any
real GEBCO file. ``try_load_gebco`` returns ``None`` cleanly when the
package or file is missing, and ``score_bathymetry`` accepts ``None``
without raising.

The other helpers operate on any duck-typed dataset that exposes the
GEBCO-style structure::

    ds.variables["lat"][:]        -> 1D array of latitudes (degrees)
    ds.variables["lon"][:]        -> 1D array of longitudes (degrees)
    ds.variables["elevation"]     -> 2D array indexed as [lat, lon],
                                     negative values mean underwater

Splitting sampling from scoring lets the tests pin each concern with
small in-memory fixtures.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from pyproj import Transformer


_GEODETIC_FORWARD = Transformer.from_crs("EPSG:4326", "EPSG:32620", always_xy=True)
_GEODETIC_INVERSE = Transformer.from_crs("EPSG:32620", "EPSG:4326", always_xy=True)


# Default sampling distances offshore, in meters. Tuned for nearshore
# gradient detection — wider than the shoreline pixel itself, closer
# than the full shelf.
DEFAULT_TRANSECT_DISTANCES_M: tuple[float, ...] = (0.0, 250.0, 500.0, 1000.0, 2000.0)

# Score thresholds derived from the historical heuristic in
# `11_score_geometry.py`. Centralized so the tests can assert against
# the same constants.
MAX_BATHY_SCORE = 20.0
STRONG_GRADIENT_M_PER_M = 0.05  # ~50 m of additional depth per 1000 m offshore
FLAT_SHELF_GRADIENT_M_PER_M = 0.005


def try_load_gebco(gebco_path: Path | None = None) -> Any | None:
    """Try to load a GEBCO bathymetry NetCDF. Returns ``None`` if unavailable.

    Defaults to ``pipeline/data/gebco/gebco_ns.nc`` relative to the
    repo root.
    """
    try:
        import netCDF4  # type: ignore[import-not-found]
    except ImportError:
        return None
    if gebco_path is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
        gebco_path = repo_root / "pipeline" / "data" / "gebco" / "gebco_ns.nc"
    if not gebco_path.exists():
        return None
    try:
        return netCDF4.Dataset(str(gebco_path))
    except (OSError, ValueError):
        return None


def _project_offset(
    lon: float, lat: float, bearing_deg: float, distance_m: float
) -> tuple[float, float]:
    """Translate a lon/lat by ``distance_m`` along a compass bearing.

    Bearing is measured clockwise from true north in degrees.
    """
    x, y = _GEODETIC_FORWARD.transform(lon, lat)
    rad = math.radians(bearing_deg)
    nx = x + distance_m * math.sin(rad)
    ny = y + distance_m * math.cos(rad)
    nlon, nlat = _GEODETIC_INVERSE.transform(nx, ny)
    return nlon, nlat


def _sample_elevation(gebco_ds: Any, lon: float, lat: float) -> float | None:
    """Return the elevation at the GEBCO cell nearest to ``(lon, lat)``."""
    try:
        lats = np.asarray(gebco_ds.variables["lat"][:])
        lons = np.asarray(gebco_ds.variables["lon"][:])
        elevation = gebco_ds.variables["elevation"]
    except (KeyError, AttributeError, TypeError):
        return None
    if lats.size == 0 or lons.size == 0:
        return None
    if not (lats.min() <= lat <= lats.max()):
        return None
    if not (lons.min() <= lon <= lons.max()):
        return None
    try:
        lat_idx = int(np.argmin(np.abs(lats - lat)))
        lon_idx = int(np.argmin(np.abs(lons - lon)))
        return float(elevation[lat_idx, lon_idx])
    except (IndexError, TypeError, ValueError):
        return None


def sample_bathymetry_transect(
    gebco_ds: Any,
    lon: float,
    lat: float,
    offshore_bearing_deg: float,
    distances_m: Sequence[float] = DEFAULT_TRANSECT_DISTANCES_M,
) -> list[float | None]:
    """Sample depths (m, positive underwater) along an offshore transect.

    Returns one entry per ``distances_m``. ``None`` is returned for any
    sample that is missing, above water, or outside the dataset.
    """
    if gebco_ds is None:
        return [None] * len(distances_m)
    samples: list[float | None] = []
    for distance in distances_m:
        if distance <= 0.0:
            sample_lon, sample_lat = lon, lat
        else:
            sample_lon, sample_lat = _project_offset(
                lon, lat, offshore_bearing_deg, distance
            )
        elevation = _sample_elevation(gebco_ds, sample_lon, sample_lat)
        if elevation is None or elevation >= 0:
            samples.append(None)
        else:
            samples.append(abs(elevation))
    return samples


def score_from_depth_samples(
    depths: Sequence[float | None],
    distances_m: Sequence[float] = DEFAULT_TRANSECT_DISTANCES_M,
) -> tuple[float, str]:
    """Score a transect of depth samples.

    Returns a tuple of ``(score, explanation)``. Score is clamped to
    ``[0, MAX_BATHY_SCORE]``.
    """
    valid = [
        (distance, depth)
        for distance, depth in zip(distances_m, depths)
        if depth is not None
    ]
    if len(valid) < 2:
        return 0.0, "Nearshore depth samples unavailable"

    near_distance, near_depth = valid[0]
    far_distance, far_depth = valid[-1]
    span_m = far_distance - near_distance
    if span_m <= 0.0:
        return 0.0, "Bathymetry transect collapsed to a single distance"

    gradient = (far_depth - near_depth) / span_m
    if gradient <= 0.0:
        return 0.0, "Nearshore depth gradient appears non-deepening offshore"

    raw = (gradient / STRONG_GRADIENT_M_PER_M) * MAX_BATHY_SCORE
    score = max(0.0, min(MAX_BATHY_SCORE, raw))

    if gradient >= STRONG_GRADIENT_M_PER_M:
        explanation = (
            f"Nearshore depth gradient appears steep ({gradient:.3f} m/m)"
        )
    elif gradient >= FLAT_SHELF_GRADIENT_M_PER_M:
        explanation = (
            f"Nearshore depth gradient appears moderate ({gradient:.3f} m/m)"
        )
    else:
        explanation = (
            f"Nearshore depth gradient appears gradual ({gradient:.3f} m/m)"
        )
    return round(score, 1), explanation


def score_bathymetry(
    centroid_lon: float,
    centroid_lat: float,
    gebco_ds: Any | None,
    *,
    offshore_bearing_deg: float | None = None,
    distances_m: Sequence[float] = DEFAULT_TRANSECT_DISTANCES_M,
) -> tuple[float, str]:
    """Score bathymetric gradient offshore of a segment.

    If ``gebco_ds`` is ``None``, returns ``(0.0, "...not available...")``.
    If ``offshore_bearing_deg`` is ``None``, falls back to a north-south
    transect (the historical behavior) so legacy callers keep working,
    but new callers should provide a real offshore bearing derived from
    the segment orientation.
    """
    if gebco_ds is None:
        return 0.0, "Bathymetry data not available"

    bearing = offshore_bearing_deg if offshore_bearing_deg is not None else 180.0
    try:
        depths = sample_bathymetry_transect(
            gebco_ds,
            centroid_lon,
            centroid_lat,
            bearing,
            distances_m=distances_m,
        )
    except Exception:  # pragma: no cover - defensive
        return 0.0, "Bathymetry lookup failed"

    return score_from_depth_samples(depths, distances_m=distances_m)
