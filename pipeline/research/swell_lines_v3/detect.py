from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.research.swell_lines.detect import angular_diff_mod180, load_chip
from pipeline.research.swell_lines_v2 import DEFAULT_PRESET_NAME, resolve_window_preset
from pipeline.research.swell_lines_v2.detect import (
    _analyze_tile,
    _valid_mask,
    _window_pixels,
    cluster_tile_votes,
    extract_tiles,
)

try:
    import rasterio
    from rasterio.warp import transform as rasterio_transform
except ImportError:  # pragma: no cover - runtime dependency guard
    rasterio = None
    rasterio_transform = None


CONFIGS_DIR = Path("pipeline/configs")
CALIBRATION_REPORT_PATH = Path("pipeline/data/calibration_report.json")
SEGMENTS_PATH = Path("pipeline/data/coastline/ns_segments.geojson")
SCORED_SEGMENTS_PATH = Path("pipeline/data/coastline/ns_scored_segments.geojson")


@dataclass(frozen=True, slots=True)
class SpotContext:
    slug: str
    point_lon: float
    point_lat: float
    segment_id: str
    segment_orientation_deg: float
    source: str


@dataclass(slots=True)
class SwellLineV3Result:
    classification: str
    cluster_azimuth_deg: float | None
    cluster_wavelength_m: float | None
    dominant_cluster_share: float
    dominant_cluster_tile_count: int
    retained_tile_count: int
    tile_count: int
    pixel_size_m: float
    window_height_m: float
    window_width_m: float
    stride_m: float
    window_preset_name: str
    cluster_median_coherence: float
    angle_bin_deg: float
    spot_slug: str | None
    segment_id: str | None
    segment_orientation_deg: float | None
    azimuth_delta_vs_segment_deg: float | None
    anchor_row: float
    anchor_col: float
    corridor_near_m: float
    corridor_far_m: float
    corridor_half_width_m: float
    roi_valid_pixel_count: int
    cluster_histogram: dict[str, int] = field(default_factory=dict)
    tile_votes: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * radius_m * math.asin(math.sqrt(a))


@lru_cache(maxsize=1)
def _load_segments() -> dict[str, dict]:
    with SEGMENTS_PATH.open() as handle:
        payload = json.load(handle)
    return {feature["properties"]["segment_id"]: feature["properties"] for feature in payload["features"]}


@lru_cache(maxsize=1)
def _load_scored_segments() -> dict[str, dict]:
    if not SCORED_SEGMENTS_PATH.exists():
        return {}
    with SCORED_SEGMENTS_PATH.open() as handle:
        payload = json.load(handle)
    return {feature["properties"]["segment_id"]: feature["properties"] for feature in payload["features"]}


def _iter_slug_matches(obj: Any, slug: str) -> list[dict]:
    matches: list[dict] = []
    if isinstance(obj, dict):
        if obj.get("slug") == slug and (obj.get("best_segment_within_distance_id") or obj.get("best_segment_id")):
            matches.append(obj)
        for value in obj.values():
            matches.extend(_iter_slug_matches(value, slug))
    elif isinstance(obj, list):
        for value in obj:
            matches.extend(_iter_slug_matches(value, slug))
    return matches


def _calibration_segment_match(slug: str) -> tuple[str, float, str] | None:
    if not CALIBRATION_REPORT_PATH.exists():
        return None
    payload = json.loads(CALIBRATION_REPORT_PATH.read_text())
    candidates = []
    for match in _iter_slug_matches(payload, slug):
        segment_id = match.get("best_segment_within_distance_id") or match.get("best_segment_id")
        distance = match.get("best_segment_within_distance_m")
        if distance is None:
            distance = match.get("best_segment_distance_m")
        distance_value = float(distance) if distance is not None else float("inf")
        orientation = match.get("best_segment_orientation_deg")
        orientation_value = float(orientation) if orientation is not None else None
        if segment_id and orientation_value is not None:
            source = "calibration-within-distance" if match.get("best_segment_within_distance_id") else "calibration-best"
            candidates.append((distance_value, str(segment_id), orientation_value, source))

    if not candidates:
        return None
    _, segment_id, orientation_deg, source = min(candidates, key=lambda item: item[0])
    return segment_id, orientation_deg, source


def _load_spot_point(slug: str) -> tuple[float, float]:
    config_path = CONFIGS_DIR / f"{slug}.json"
    with config_path.open() as handle:
        payload = json.load(handle)
    point = payload.get("point")
    if not point:
        raise ValueError(f"Config for {slug} is missing point coordinates.")
    return float(point["lon"]), float(point["lat"])


def _nearest_segment_for_point(lon: float, lat: float) -> tuple[str, float]:
    segments = _load_segments()
    best_id = None
    best_distance = float("inf")
    best_orientation = None
    for segment_id, props in segments.items():
        distance = _haversine_m(lon, lat, float(props["centroid_lon"]), float(props["centroid_lat"]))
        if distance < best_distance:
            best_distance = distance
            best_id = segment_id
            best_orientation = float(props["orientation_deg"])
    if best_id is None or best_orientation is None:  # pragma: no cover - defensive guard
        raise RuntimeError("No coastline segments available for spot matching.")
    return best_id, best_orientation


def _best_scored_segment_for_point(lon: float, lat: float, *, radius_m: float = 1_500.0) -> tuple[str, float] | None:
    scored = _load_scored_segments()
    candidates: list[tuple[float, float, str, float]] = []
    for segment_id, props in scored.items():
        distance = _haversine_m(lon, lat, float(props["centroid_lon"]), float(props["centroid_lat"]))
        if distance > radius_m:
            continue
        score = float(props.get("total_score", 0.0))
        orientation = float(props["orientation_deg"])
        candidates.append((-score, distance, segment_id, orientation))
    if not candidates:
        return None
    _, _, segment_id, orientation = min(candidates)
    return segment_id, orientation


@lru_cache(maxsize=None)
def load_spot_context(slug: str) -> SpotContext:
    point_lon, point_lat = _load_spot_point(slug)
    calibration_match = _calibration_segment_match(slug)
    if calibration_match is not None:
        segment_id, orientation_deg, source = calibration_match
    else:
        scored_match = _best_scored_segment_for_point(point_lon, point_lat)
        if scored_match is not None:
            segment_id, orientation_deg = scored_match
            source = "best-scored-nearby-segment"
        else:
            segment_id, orientation_deg = _nearest_segment_for_point(point_lon, point_lat)
            source = "nearest-segment"
    return SpotContext(
        slug=slug,
        point_lon=point_lon,
        point_lat=point_lat,
        segment_id=segment_id,
        segment_orientation_deg=orientation_deg,
        source=source,
    )


def build_offshore_corridor_mask(
    *,
    shape: tuple[int, int],
    anchor_row: float,
    anchor_col: float,
    orientation_deg: float,
    pixel_size_m: float,
    near_m: float,
    far_m: float,
    alongshore_half_width_m: float,
) -> np.ndarray:
    row_grid, col_grid = np.indices(shape, dtype=float)
    east_m = (col_grid - anchor_col) * pixel_size_m
    north_m = -(row_grid - anchor_row) * pixel_size_m

    orientation_rad = math.radians(orientation_deg)
    normal_east = math.sin(orientation_rad)
    normal_north = math.cos(orientation_rad)
    tangent_east = math.sin(orientation_rad - math.pi / 2.0)
    tangent_north = math.cos(orientation_rad - math.pi / 2.0)

    offshore_m = east_m * normal_east + north_m * normal_north
    alongshore_m = east_m * tangent_east + north_m * tangent_north
    return (
        (offshore_m >= near_m)
        & (offshore_m <= far_m)
        & (np.abs(alongshore_m) <= alongshore_half_width_m)
    )


def _resolve_anchor_pixels(
    chip_path: Path,
    *,
    spot_slug: str | None,
    anchor_row: float | None,
    anchor_col: float | None,
    segment_orientation_deg: float | None,
) -> tuple[float, float, float | None, str | None, str | None]:
    if anchor_row is not None and anchor_col is not None and segment_orientation_deg is not None:
        return float(anchor_row), float(anchor_col), float(segment_orientation_deg), None, spot_slug

    if spot_slug is None:
        raise ValueError("detect_swell_lines_v3 requires either spot_slug or manual anchor/orientation inputs.")

    context = load_spot_context(spot_slug)
    if rasterio is None:  # pragma: no cover - runtime guard
        raise RuntimeError("rasterio is required to derive spot anchors from georeferenced chips.")

    with rasterio.open(chip_path) as dataset:
        if dataset.crs:
            xs, ys = rasterio_transform("EPSG:4326", dataset.crs, [context.point_lon], [context.point_lat])
            anchor_x, anchor_y = xs[0], ys[0]
        else:  # pragma: no cover - fallback for ungeoreferenced files
            anchor_x, anchor_y = context.point_lon, context.point_lat
        row, col = dataset.index(anchor_x, anchor_y)
    return float(row), float(col), context.segment_orientation_deg, context.segment_id, context.slug


def detect_swell_lines_v3(
    chip_path: Path | str,
    *,
    spot_slug: str | None = None,
    anchor_row: float | None = None,
    anchor_col: float | None = None,
    segment_orientation_deg: float | None = None,
    corridor_near_m: float = 250.0,
    corridor_far_m: float = 1750.0,
    corridor_half_width_m: float = 900.0,
    preset_name: str = DEFAULT_PRESET_NAME,
    window_height_m: float | None = None,
    window_width_m: float | None = None,
    stride_m: float | None = None,
    min_valid_fraction: float = 0.75,
    mask_erosion_iterations: int = 2,
    min_wavelength_m: float = 80.0,
    max_wavelength_m: float = 250.0,
    noise_floor_quantile: float = 0.5,
    min_local_coherence: float = 4.0,
    min_local_peak_fraction: float = 0.1,
    theta_step_deg: float = 2.0,
    angle_bin_deg: float = 15.0,
    min_cluster_share: float = 0.5,
    min_cluster_tile_count: int = 3,
    min_cluster_median_coherence: float = 4.0,
) -> SwellLineV3Result:
    path = Path(chip_path)
    preset = resolve_window_preset(preset_name)
    window_height_m = window_height_m if window_height_m is not None else preset.window_height_m
    window_width_m = window_width_m if window_width_m is not None else preset.window_width_m
    stride_m = stride_m if stride_m is not None else preset.stride_m

    signal, mask, pixel_size_m = load_chip(path)
    anchor_row, anchor_col, resolved_orientation_deg, segment_id, resolved_slug = _resolve_anchor_pixels(
        path,
        spot_slug=spot_slug,
        anchor_row=anchor_row,
        anchor_col=anchor_col,
        segment_orientation_deg=segment_orientation_deg,
    )
    assert resolved_orientation_deg is not None

    corridor_mask = build_offshore_corridor_mask(
        shape=signal.shape,
        anchor_row=anchor_row,
        anchor_col=anchor_col,
        orientation_deg=resolved_orientation_deg,
        pixel_size_m=pixel_size_m,
        near_m=corridor_near_m,
        far_m=corridor_far_m,
        alongshore_half_width_m=corridor_half_width_m,
    )
    valid_mask = _valid_mask(signal, mask, mask_erosion_iterations) & corridor_mask
    roi_valid_pixel_count = int(valid_mask.sum())

    window_height_px, window_width_px, stride_px = _window_pixels(
        window_height_m,
        window_width_m,
        stride_m,
        pixel_size_m,
    )
    tiles = extract_tiles(
        signal,
        valid_mask,
        window_height_px=window_height_px,
        window_width_px=window_width_px,
        stride_px=stride_px,
        min_valid_fraction=min_valid_fraction,
    )
    theta_values = np.arange(0.0, 180.0, theta_step_deg)
    tile_votes = [
        vote
        for vote in (
            _analyze_tile(
                signal,
                valid_mask,
                tile,
                pixel_size_m=pixel_size_m,
                theta_values=theta_values,
                min_wavelength_m=min_wavelength_m,
                max_wavelength_m=max_wavelength_m,
                noise_floor_quantile=noise_floor_quantile,
                min_local_coherence=min_local_coherence,
                min_local_peak_fraction=min_local_peak_fraction,
            )
            for tile in tiles
        )
        if vote is not None
    ]
    summary = cluster_tile_votes(
        tile_votes,
        angle_bin_deg=angle_bin_deg,
        min_cluster_share=min_cluster_share,
        min_cluster_tile_count=min_cluster_tile_count,
        min_cluster_median_coherence=min_cluster_median_coherence,
    )

    azimuth_delta_vs_segment_deg = angular_diff_mod180(summary.cluster_azimuth_deg, resolved_orientation_deg)
    notes = list(summary.notes)
    if roi_valid_pixel_count == 0:
        notes.append("empty_corridor_roi")

    return SwellLineV3Result(
        classification=summary.classification,
        cluster_azimuth_deg=summary.cluster_azimuth_deg,
        cluster_wavelength_m=summary.cluster_wavelength_m,
        dominant_cluster_share=summary.dominant_cluster_share,
        dominant_cluster_tile_count=summary.dominant_cluster_tile_count,
        retained_tile_count=summary.retained_tile_count,
        tile_count=len(tiles),
        pixel_size_m=pixel_size_m,
        window_height_m=float(window_height_m),
        window_width_m=float(window_width_m),
        stride_m=float(stride_m),
        window_preset_name=preset.name,
        cluster_median_coherence=summary.cluster_median_coherence,
        angle_bin_deg=angle_bin_deg,
        spot_slug=resolved_slug,
        segment_id=segment_id,
        segment_orientation_deg=resolved_orientation_deg,
        azimuth_delta_vs_segment_deg=azimuth_delta_vs_segment_deg,
        anchor_row=anchor_row,
        anchor_col=anchor_col,
        corridor_near_m=corridor_near_m,
        corridor_far_m=corridor_far_m,
        corridor_half_width_m=corridor_half_width_m,
        roi_valid_pixel_count=roi_valid_pixel_count,
        cluster_histogram=summary.cluster_histogram,
        tile_votes=[asdict(vote) for vote in tile_votes],
        notes=notes,
    )
