from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.research.swell_lines.detect import load_chip
from pipeline.research.swell_lines_v2 import DEFAULT_PRESET_NAME, resolve_window_preset

try:
    from skimage.transform import radon
except ImportError:  # pragma: no cover - runtime dependency guard
    radon = None


@dataclass(frozen=True, slots=True)
class TileWindow:
    row_start: int
    col_start: int
    row_stop: int
    col_stop: int
    valid_fraction: float


@dataclass(frozen=True, slots=True)
class TileVote:
    row_start: int
    col_start: int
    row_stop: int
    col_stop: int
    valid_fraction: float
    azimuth_deg: float
    wavelength_m: float
    coherence: float
    peak_fraction: float


@dataclass(slots=True)
class ClusterSummary:
    classification: str
    dominant_cluster_share: float
    dominant_cluster_tile_count: int
    retained_tile_count: int
    cluster_azimuth_deg: float | None
    cluster_wavelength_m: float | None
    cluster_median_coherence: float
    dominant_cluster_bin_deg: float | None
    cluster_histogram: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SwellLineV2Result:
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
    cluster_histogram: dict[str, int] = field(default_factory=dict)
    tile_votes: list[TileVote] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _binary_erode(mask: np.ndarray, iterations: int) -> np.ndarray:
    result = np.asarray(mask, dtype=bool)
    for _ in range(max(iterations, 0)):
        padded = np.pad(result, 1, constant_values=False)
        neighborhoods = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                neighborhoods.append(
                    padded[
                        1 + dy : 1 + dy + result.shape[0],
                        1 + dx : 1 + dx + result.shape[1],
                    ]
                )
        result = np.logical_and.reduce(neighborhoods)
    return result


def _valid_mask(
    signal: np.ndarray,
    mask: np.ndarray | None,
    erosion_iterations: int,
) -> np.ndarray:
    valid = np.isfinite(signal)
    if mask is not None:
        valid &= np.asarray(mask, dtype=bool)
    if erosion_iterations:
        valid = _binary_erode(valid, erosion_iterations)
    return valid


def _window_pixels(window_height_m: float, window_width_m: float, stride_m: float, pixel_size_m: float) -> tuple[int, int, int]:
    return (
        max(8, int(round(window_height_m / pixel_size_m))),
        max(8, int(round(window_width_m / pixel_size_m))),
        max(1, int(round(stride_m / pixel_size_m))),
    )


def extract_tiles(
    signal: np.ndarray,
    valid_mask: np.ndarray,
    *,
    window_height_px: int,
    window_width_px: int,
    stride_px: int,
    min_valid_fraction: float = 0.75,
) -> list[TileWindow]:
    rows, cols = signal.shape
    if rows < window_height_px or cols < window_width_px:
        return []

    tiles: list[TileWindow] = []
    for row_start in range(0, rows - window_height_px + 1, stride_px):
        row_stop = row_start + window_height_px
        for col_start in range(0, cols - window_width_px + 1, stride_px):
            col_stop = col_start + window_width_px
            fraction = float(valid_mask[row_start:row_stop, col_start:col_stop].mean())
            if fraction < min_valid_fraction:
                continue
            tiles.append(
                TileWindow(
                    row_start=row_start,
                    col_start=col_start,
                    row_stop=row_stop,
                    col_stop=col_stop,
                    valid_fraction=fraction,
                )
            )
    return tiles


def _prepare_tile(signal: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    working = np.asarray(signal, dtype=float).copy()
    if valid_mask.any():
        fill_value = float(np.nanmean(working[valid_mask]))
        working[~valid_mask] = fill_value
        working -= fill_value
    else:
        working[:] = 0.0
    window = np.outer(np.hanning(working.shape[0]), np.hanning(working.shape[1]))
    return np.nan_to_num(working * window, copy=False)


def _circular_mean_mod180(angles_deg: list[float]) -> float | None:
    if not angles_deg:
        return None
    doubled = np.radians(np.asarray(angles_deg) * 2.0)
    mean_vector = np.mean(np.exp(1j * doubled))
    if mean_vector == 0:
        return None
    return float((np.degrees(np.angle(mean_vector)) / 2.0) % 180.0)


def _analyze_projection(
    projection: np.ndarray,
    *,
    pixel_size_m: float,
    min_wavelength_m: float,
    max_wavelength_m: float,
    noise_floor_quantile: float,
) -> tuple[float, float, float] | None:
    centered = np.asarray(projection, dtype=float)
    centered = (centered - centered.mean()) * np.hanning(centered.shape[0])

    power = np.abs(np.fft.rfft(centered)) ** 2
    frequencies = np.fft.rfftfreq(centered.shape[0], d=pixel_size_m)
    with np.errstate(divide="ignore", invalid="ignore"):
        wavelengths = np.where(frequencies > 0, 1.0 / frequencies, np.inf)

    candidate_mask = (
        np.isfinite(wavelengths)
        & (wavelengths >= min_wavelength_m)
        & (wavelengths <= max_wavelength_m)
    )
    candidate_power = power[candidate_mask]
    positive_power = candidate_power[candidate_power > 0]
    if positive_power.size == 0:
        return None

    bounded_power = np.where(candidate_mask, power, 0.0)
    peak_index = int(np.argmax(bounded_power))
    noise_floor = float(np.quantile(positive_power, noise_floor_quantile))
    coherence = float(power[peak_index] / max(noise_floor, 1e-12))
    wavelength_m = float(wavelengths[peak_index])

    left = max(peak_index - 1, 0)
    right = min(peak_index + 2, power.shape[0])
    peak_fraction = float(power[left:right].sum() / max(candidate_power.sum(), 1e-12))
    return wavelength_m, coherence, peak_fraction


def _analyze_tile(
    signal: np.ndarray,
    valid_mask: np.ndarray,
    tile: TileWindow,
    *,
    pixel_size_m: float,
    theta_values: np.ndarray,
    min_wavelength_m: float,
    max_wavelength_m: float,
    noise_floor_quantile: float,
    min_local_coherence: float,
    min_local_peak_fraction: float,
) -> TileVote | None:
    tile_signal = signal[tile.row_start : tile.row_stop, tile.col_start : tile.col_stop]
    tile_valid = valid_mask[tile.row_start : tile.row_stop, tile.col_start : tile.col_stop]
    prepared = _prepare_tile(tile_signal, tile_valid)

    if radon is None:  # pragma: no cover - runtime guard
        raise RuntimeError("swell_lines_v2 requires scikit-image for Radon transforms.")

    sinogram = radon(prepared, theta=theta_values, circle=False, preserve_range=True)
    angle_energy = np.var(sinogram, axis=0)
    best_index = int(np.argmax(angle_energy))
    best_theta = float(theta_values[best_index])
    azimuth_deg = float((90.0 - best_theta) % 180.0)

    projection = np.asarray(sinogram[:, best_index], dtype=float)
    spectral = _analyze_projection(
        projection,
        pixel_size_m=pixel_size_m,
        min_wavelength_m=min_wavelength_m,
        max_wavelength_m=max_wavelength_m,
        noise_floor_quantile=noise_floor_quantile,
    )
    if spectral is None:
        return None

    wavelength_m, coherence, peak_fraction = spectral
    if coherence < min_local_coherence or peak_fraction < min_local_peak_fraction:
        return None

    return TileVote(
        row_start=tile.row_start,
        col_start=tile.col_start,
        row_stop=tile.row_stop,
        col_stop=tile.col_stop,
        valid_fraction=tile.valid_fraction,
        azimuth_deg=azimuth_deg,
        wavelength_m=wavelength_m,
        coherence=coherence,
        peak_fraction=peak_fraction,
    )


def cluster_tile_votes(
    votes: list[TileVote],
    *,
    angle_bin_deg: float = 15.0,
    min_cluster_share: float = 0.5,
    min_cluster_tile_count: int = 3,
    min_cluster_median_coherence: float = 4.0,
) -> ClusterSummary:
    if not votes:
        return ClusterSummary(
            classification="flat",
            dominant_cluster_share=0.0,
            dominant_cluster_tile_count=0,
            retained_tile_count=0,
            cluster_azimuth_deg=None,
            cluster_wavelength_m=None,
            cluster_median_coherence=0.0,
            dominant_cluster_bin_deg=None,
            notes=["no_retained_tiles"],
        )

    bins: dict[float, list[TileVote]] = {}
    for vote in votes:
        bin_index = int(((vote.azimuth_deg + angle_bin_deg / 2.0) % 180.0) // angle_bin_deg)
        bin_center = float((bin_index * angle_bin_deg) % 180.0)
        bins.setdefault(bin_center, []).append(vote)

    dominant_bin, dominant_votes = max(bins.items(), key=lambda item: len(item[1]))
    dominant_share = len(dominant_votes) / len(votes)
    cluster_azimuth = _circular_mean_mod180([vote.azimuth_deg for vote in dominant_votes])
    cluster_wavelength = float(np.median([vote.wavelength_m for vote in dominant_votes]))
    cluster_median_coherence = float(np.median([vote.coherence for vote in dominant_votes]))
    classification = (
        "organized"
        if dominant_share >= min_cluster_share
        and len(dominant_votes) >= min_cluster_tile_count
        and cluster_median_coherence >= min_cluster_median_coherence
        else "flat"
    )

    notes: list[str] = []
    if classification == "flat" and dominant_share < min_cluster_share:
        notes.append("dominant_cluster_share_below_threshold")
    if classification == "flat" and len(dominant_votes) < min_cluster_tile_count:
        notes.append("dominant_cluster_tile_count_below_threshold")
    if classification == "flat" and cluster_median_coherence < min_cluster_median_coherence:
        notes.append("cluster_median_coherence_below_threshold")

    histogram = {f"{bin_center:.1f}": len(cluster_votes) for bin_center, cluster_votes in sorted(bins.items())}
    return ClusterSummary(
        classification=classification,
        dominant_cluster_share=dominant_share,
        dominant_cluster_tile_count=len(dominant_votes),
        retained_tile_count=len(votes),
        cluster_azimuth_deg=cluster_azimuth,
        cluster_wavelength_m=cluster_wavelength,
        cluster_median_coherence=cluster_median_coherence,
        dominant_cluster_bin_deg=dominant_bin,
        cluster_histogram=histogram,
        notes=notes,
    )


def detect_swell_lines_v2(
    chip_path: Path | str,
    *,
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
) -> SwellLineV2Result:
    preset = resolve_window_preset(preset_name)
    window_height_m = window_height_m if window_height_m is not None else preset.window_height_m
    window_width_m = window_width_m if window_width_m is not None else preset.window_width_m
    stride_m = stride_m if stride_m is not None else preset.stride_m

    signal, mask, pixel_size_m = load_chip(chip_path)
    valid_mask = _valid_mask(signal, mask, mask_erosion_iterations)
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
    if theta_values.size == 0:
        raise ValueError("theta_step_deg must produce at least one Radon angle.")

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

    return SwellLineV2Result(
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
        cluster_histogram=summary.cluster_histogram,
        tile_votes=tile_votes,
        notes=summary.notes,
    )
