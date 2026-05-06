from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pywt
from scipy.ndimage import map_coordinates

from pipeline.research.swell_lines.detect import angular_diff_mod180, load_chip
from pipeline.research.swell_lines_v2.detect import _valid_mask
from pipeline.research.swell_lines_v3.detect import (
    SpotContext,
    _resolve_anchor_pixels,
    build_offshore_corridor_mask,
    load_spot_context,
)


@dataclass(frozen=True, slots=True)
class TransectWaveletResult:
    wavelength_m: float
    coherence: float
    peak_fraction: float
    valid_fraction: float
    along_offset_m: float


@dataclass(frozen=True, slots=True)
class AzimuthCandidateResult:
    azimuth_deg: float
    total_transects: int
    retained_transect_count: int
    retained_transect_share: float
    wavelength_cluster_share: float
    cluster_wavelength_m: float | None
    cluster_median_coherence: float
    classification: str
    transects: list[TransectWaveletResult]
    notes: list[str]

    @property
    def score(self) -> float:
        if self.classification != "organized":
            return self.retained_transect_share * self.wavelength_cluster_share
        return self.retained_transect_share * self.wavelength_cluster_share * self.cluster_median_coherence


@dataclass(slots=True)
class SwellLineV4Result:
    classification: str
    cluster_azimuth_deg: float | None
    cluster_wavelength_m: float | None
    retained_transect_share: float
    wavelength_cluster_share: float
    retained_transect_count: int
    total_transects: int
    pixel_size_m: float
    spot_slug: str | None
    segment_id: str | None
    segment_orientation_deg: float | None
    azimuth_delta_vs_segment_deg: float | None
    corridor_near_m: float
    corridor_far_m: float
    corridor_half_width_m: float
    roi_valid_pixel_count: int
    transect_spacing_m: float
    azimuth_search_half_width_deg: float
    azimuth_step_deg: float
    cluster_median_coherence: float
    transects: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sample_transect(
    signal: np.ndarray,
    valid_mask: np.ndarray,
    *,
    anchor_row: float,
    anchor_col: float,
    azimuth_deg: float,
    along_offset_m: float,
    near_m: float,
    far_m: float,
    pixel_size_m: float,
    min_valid_fraction: float,
) -> tuple[np.ndarray, float] | None:
    if far_m <= near_m:
        return None

    orientation_rad = np.radians(azimuth_deg)
    normal_east = np.sin(orientation_rad)
    normal_north = np.cos(orientation_rad)
    tangent_east = np.sin(orientation_rad - np.pi / 2.0)
    tangent_north = np.cos(orientation_rad - np.pi / 2.0)

    distances = np.arange(near_m, far_m + pixel_size_m * 0.5, pixel_size_m)
    east_offsets = tangent_east * along_offset_m + normal_east * distances
    north_offsets = tangent_north * along_offset_m + normal_north * distances
    rows = anchor_row - (north_offsets / pixel_size_m)
    cols = anchor_col + (east_offsets / pixel_size_m)

    inside = (
        (rows >= 0)
        & (rows <= signal.shape[0] - 1)
        & (cols >= 0)
        & (cols <= signal.shape[1] - 1)
    )
    if inside.sum() < 32:
        return None

    rows = rows[inside]
    cols = cols[inside]
    sampled_signal = map_coordinates(signal, [rows, cols], order=1, mode="nearest")
    sampled_valid = map_coordinates(valid_mask.astype(float), [rows, cols], order=0, mode="constant", cval=0.0) > 0.5
    valid_fraction = float(sampled_valid.mean())
    if valid_fraction < min_valid_fraction or sampled_valid.sum() < 24:
        return None

    cleaned = sampled_signal.astype(float)
    fill_value = float(np.mean(cleaned[sampled_valid]))
    cleaned[~sampled_valid] = fill_value
    return cleaned, valid_fraction


def analyze_transect_wavelet(
    signal_1d: np.ndarray,
    *,
    pixel_size_m: float,
    min_wavelength_m: float = 80.0,
    max_wavelength_m: float = 250.0,
    num_scales: int = 48,
    noise_floor_quantile: float = 0.5,
) -> TransectWaveletResult | None:
    signal = np.asarray(signal_1d, dtype=float)
    if signal.size < 32 or np.nanstd(signal) <= 1e-9:
        return None

    centered = signal - np.nanmean(signal)
    centered *= np.hanning(centered.shape[0])

    target_wavelengths = np.linspace(min_wavelength_m, max_wavelength_m, num_scales)
    central_frequency = pywt.central_frequency("morl")
    scales = central_frequency * target_wavelengths / pixel_size_m
    coefficients, frequencies = pywt.cwt(centered, scales, "morl", sampling_period=pixel_size_m)
    with np.errstate(divide="ignore", invalid="ignore"):
        wavelengths = np.where(frequencies > 0, 1.0 / frequencies, np.inf)

    power = np.abs(coefficients) ** 2
    scale_power = np.nanmean(power, axis=1)
    positive = scale_power[scale_power > 0]
    if positive.size == 0:
        return None

    peak_index = int(np.argmax(scale_power))
    coherence = float(scale_power[peak_index] / max(np.quantile(positive, noise_floor_quantile), 1e-12))
    left = max(peak_index - 1, 0)
    right = min(peak_index + 2, scale_power.shape[0])
    peak_fraction = float(scale_power[left:right].sum() / max(scale_power.sum(), 1e-12))
    return TransectWaveletResult(
        wavelength_m=float(wavelengths[peak_index]),
        coherence=coherence,
        peak_fraction=peak_fraction,
        valid_fraction=1.0,
        along_offset_m=0.0,
    )


def _evaluate_azimuth_candidate(
    signal: np.ndarray,
    valid_mask: np.ndarray,
    *,
    anchor_row: float,
    anchor_col: float,
    azimuth_deg: float,
    pixel_size_m: float,
    corridor_near_m: float,
    corridor_far_m: float,
    corridor_half_width_m: float,
    transect_spacing_m: float,
    min_transect_valid_fraction: float,
    min_wavelength_m: float,
    max_wavelength_m: float,
    min_transect_coherence: float,
    min_peak_fraction: float,
    min_retained_share: float,
    min_retained_count: int,
    min_wavelength_cluster_share: float,
    wavelength_bin_m: float,
) -> AzimuthCandidateResult:
    offsets = np.arange(-corridor_half_width_m, corridor_half_width_m + transect_spacing_m * 0.5, transect_spacing_m)
    sampled_transects = 0
    retained: list[TransectWaveletResult] = []

    for along_offset_m in offsets:
        sampled = _sample_transect(
            signal,
            valid_mask,
            anchor_row=anchor_row,
            anchor_col=anchor_col,
            azimuth_deg=azimuth_deg,
            along_offset_m=float(along_offset_m),
            near_m=corridor_near_m,
            far_m=corridor_far_m,
            pixel_size_m=pixel_size_m,
            min_valid_fraction=min_transect_valid_fraction,
        )
        if sampled is None:
            continue
        transect, valid_fraction = sampled
        sampled_transects += 1
        analysis = analyze_transect_wavelet(
            transect,
            pixel_size_m=pixel_size_m,
            min_wavelength_m=min_wavelength_m,
            max_wavelength_m=max_wavelength_m,
        )
        if analysis is None:
            continue
        if analysis.coherence < min_transect_coherence or analysis.peak_fraction < min_peak_fraction:
            continue
        retained.append(
            TransectWaveletResult(
                wavelength_m=analysis.wavelength_m,
                coherence=analysis.coherence,
                peak_fraction=analysis.peak_fraction,
                valid_fraction=valid_fraction,
                along_offset_m=float(along_offset_m),
            )
        )

    if sampled_transects == 0:
        return AzimuthCandidateResult(
            azimuth_deg=azimuth_deg,
            total_transects=0,
            retained_transect_count=0,
            retained_transect_share=0.0,
            wavelength_cluster_share=0.0,
            cluster_wavelength_m=None,
            cluster_median_coherence=0.0,
            classification="flat",
            transects=[],
            notes=["no_valid_transects"],
        )

    retained_share = len(retained) / sampled_transects
    if not retained:
        return AzimuthCandidateResult(
            azimuth_deg=azimuth_deg,
            total_transects=sampled_transects,
            retained_transect_count=0,
            retained_transect_share=0.0,
            wavelength_cluster_share=0.0,
            cluster_wavelength_m=None,
            cluster_median_coherence=0.0,
            classification="flat",
            transects=[],
            notes=["no_retained_transects"],
        )

    clusters: dict[float, list[TransectWaveletResult]] = {}
    for transect in retained:
        center = round(transect.wavelength_m / wavelength_bin_m) * wavelength_bin_m
        clusters.setdefault(center, []).append(transect)
    dominant_cluster = max(clusters.values(), key=len)
    dominant_share = len(dominant_cluster) / len(retained)
    cluster_wavelength_m = float(np.median([item.wavelength_m for item in dominant_cluster]))
    cluster_median_coherence = float(np.median([item.coherence for item in dominant_cluster]))
    classification = (
        "organized"
        if retained_share >= min_retained_share
        and len(dominant_cluster) >= min_retained_count
        and dominant_share >= min_wavelength_cluster_share
        and cluster_median_coherence >= min_transect_coherence
        else "flat"
    )

    notes: list[str] = []
    if classification == "flat" and retained_share < min_retained_share:
        notes.append("retained_share_below_threshold")
    if classification == "flat" and len(dominant_cluster) < min_retained_count:
        notes.append("retained_count_below_threshold")
    if classification == "flat" and dominant_share < min_wavelength_cluster_share:
        notes.append("wavelength_cluster_share_below_threshold")

    return AzimuthCandidateResult(
        azimuth_deg=azimuth_deg,
        total_transects=sampled_transects,
        retained_transect_count=len(retained),
        retained_transect_share=retained_share,
        wavelength_cluster_share=dominant_share,
        cluster_wavelength_m=cluster_wavelength_m,
        cluster_median_coherence=cluster_median_coherence,
        classification=classification,
        transects=retained,
        notes=notes,
    )


def detect_swell_lines_v4(
    chip_path: Path | str,
    *,
    spot_slug: str | None = None,
    anchor_row: float | None = None,
    anchor_col: float | None = None,
    segment_orientation_deg: float | None = None,
    corridor_near_m: float = 250.0,
    corridor_far_m: float = 1750.0,
    corridor_half_width_m: float = 900.0,
    mask_erosion_iterations: int = 2,
    min_wavelength_m: float = 80.0,
    max_wavelength_m: float = 250.0,
    transect_spacing_m: float = 100.0,
    min_transect_valid_fraction: float = 0.6,
    min_transect_coherence: float = 3.5,
    min_peak_fraction: float = 0.2,
    min_retained_share: float = 0.4,
    min_retained_count: int = 4,
    min_wavelength_cluster_share: float = 0.5,
    wavelength_bin_m: float = 20.0,
    azimuth_search_half_width_deg: float = 36.0,
    azimuth_step_deg: float = 6.0,
) -> SwellLineV4Result:
    path = Path(chip_path)
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

    if roi_valid_pixel_count == 0:
        return SwellLineV4Result(
            classification="flat",
            cluster_azimuth_deg=None,
            cluster_wavelength_m=None,
            retained_transect_share=0.0,
            wavelength_cluster_share=0.0,
            retained_transect_count=0,
            total_transects=0,
            pixel_size_m=pixel_size_m,
            spot_slug=resolved_slug,
            segment_id=segment_id,
            segment_orientation_deg=resolved_orientation_deg,
            azimuth_delta_vs_segment_deg=None,
            corridor_near_m=corridor_near_m,
            corridor_far_m=corridor_far_m,
            corridor_half_width_m=corridor_half_width_m,
            roi_valid_pixel_count=0,
            transect_spacing_m=transect_spacing_m,
            azimuth_search_half_width_deg=azimuth_search_half_width_deg,
            azimuth_step_deg=azimuth_step_deg,
            cluster_median_coherence=0.0,
            notes=["empty_corridor_roi"],
        )

    candidate_offsets = np.arange(-azimuth_search_half_width_deg, azimuth_search_half_width_deg + azimuth_step_deg * 0.5, azimuth_step_deg)
    candidates = [
        _evaluate_azimuth_candidate(
            signal,
            valid_mask,
            anchor_row=anchor_row,
            anchor_col=anchor_col,
            azimuth_deg=float((resolved_orientation_deg + offset) % 180.0),
            pixel_size_m=pixel_size_m,
            corridor_near_m=corridor_near_m,
            corridor_far_m=corridor_far_m,
            corridor_half_width_m=corridor_half_width_m,
            transect_spacing_m=transect_spacing_m,
            min_transect_valid_fraction=min_transect_valid_fraction,
            min_wavelength_m=min_wavelength_m,
            max_wavelength_m=max_wavelength_m,
            min_transect_coherence=min_transect_coherence,
            min_peak_fraction=min_peak_fraction,
            min_retained_share=min_retained_share,
            min_retained_count=min_retained_count,
            min_wavelength_cluster_share=min_wavelength_cluster_share,
            wavelength_bin_m=wavelength_bin_m,
        )
        for offset in candidate_offsets
    ]
    best = max(
        candidates,
        key=lambda candidate: (
            candidate.score,
            candidate.retained_transect_share,
            candidate.retained_transect_count,
            -abs(((candidate.azimuth_deg - resolved_orientation_deg + 90.0) % 180.0) - 90.0),
        ),
    )
    azimuth_delta_vs_segment_deg = angular_diff_mod180(best.azimuth_deg, resolved_orientation_deg)

    return SwellLineV4Result(
        classification=best.classification,
        cluster_azimuth_deg=best.azimuth_deg,
        cluster_wavelength_m=best.cluster_wavelength_m,
        retained_transect_share=best.retained_transect_share,
        wavelength_cluster_share=best.wavelength_cluster_share,
        retained_transect_count=best.retained_transect_count,
        total_transects=best.total_transects,
        pixel_size_m=pixel_size_m,
        spot_slug=resolved_slug,
        segment_id=segment_id,
        segment_orientation_deg=resolved_orientation_deg,
        azimuth_delta_vs_segment_deg=azimuth_delta_vs_segment_deg,
        corridor_near_m=corridor_near_m,
        corridor_far_m=corridor_far_m,
        corridor_half_width_m=corridor_half_width_m,
        roi_valid_pixel_count=roi_valid_pixel_count,
        transect_spacing_m=transect_spacing_m,
        azimuth_search_half_width_deg=azimuth_search_half_width_deg,
        azimuth_step_deg=azimuth_step_deg,
        cluster_median_coherence=best.cluster_median_coherence,
        transects=[asdict(item) for item in best.transects],
        notes=best.notes,
    )
