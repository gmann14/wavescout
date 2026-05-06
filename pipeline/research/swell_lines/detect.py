from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.research.swell_lines import WATER_SCL_VALUE

try:
    import rasterio
except ImportError:  # pragma: no cover - optional runtime dependency
    rasterio = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional runtime dependency
    Image = None


@dataclass(slots=True)
class SwellLineResult:
    wavelength_m: float | None
    azimuth_deg: float | None
    peak_power: float
    classification: str
    peak_snr: float
    peak_fraction: float
    noise_floor: float
    valid_pixel_count: int
    pixel_size_m: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def angular_diff_mod180(a_deg: float | None, b_deg: float | None) -> float | None:
    if a_deg is None or b_deg is None:
        return None
    diff = abs((a_deg - b_deg) % 180.0)
    return min(diff, 180.0 - diff)


def _mask_from_band(mask_band: np.ndarray | None) -> np.ndarray | None:
    if mask_band is None:
        return None
    band = np.asarray(mask_band)
    finite = np.isfinite(band)
    if not finite.any():
        return None
    unique_values = np.unique(band[finite])
    if unique_values.size and unique_values.max() <= 1:
        return band > 0.5
    if unique_values.size and unique_values.max() <= 11 and unique_values.min() >= 0:
        return band == WATER_SCL_VALUE
    return finite & (band > 0)


def _coerce_band_first(array: np.ndarray) -> np.ndarray:
    if array.ndim != 3:
        return array
    if array.shape[0] <= 4:
        return array
    if array.shape[-1] <= 4:
        return np.moveaxis(array, -1, 0)
    return array


def _load_numpy_chip(path: Path) -> tuple[np.ndarray, np.ndarray | None, float]:
    suffix = path.suffix.lower()
    if suffix == ".npy":
        array = np.load(path, allow_pickle=False)
        band_first = _coerce_band_first(np.asarray(array))
        if band_first.ndim == 2:
            return band_first.astype(float), None, 10.0
        signal = band_first[0].astype(float)
        mask = _mask_from_band(band_first[1] if band_first.shape[0] > 1 else None)
        return signal, mask, 10.0

    with np.load(path, allow_pickle=False) as loaded:
        if "signal" in loaded:
            signal = loaded["signal"].astype(float)
            mask = _mask_from_band(loaded["mask"]) if "mask" in loaded else None
            pixel_size_m = float(loaded["pixel_size_m"]) if "pixel_size_m" in loaded else 10.0
            return signal, mask, pixel_size_m

        if "chip" in loaded:
            band_first = _coerce_band_first(np.asarray(loaded["chip"]))
        else:
            band_first = _coerce_band_first(np.asarray(loaded[loaded.files[0]]))

        pixel_size_m = float(loaded["pixel_size_m"]) if "pixel_size_m" in loaded else 10.0

    if band_first.ndim == 2:
        return band_first.astype(float), None, pixel_size_m

    signal = band_first[0].astype(float)
    mask = _mask_from_band(band_first[1] if band_first.shape[0] > 1 else None)
    return signal, mask, pixel_size_m


def _load_tiff_chip(path: Path) -> tuple[np.ndarray, np.ndarray | None, float]:
    if rasterio is not None:  # pragma: no branch - runtime choice
        with rasterio.open(path) as dataset:
            array = dataset.read()
            pixel_size_m = abs(float(dataset.transform.a)) or 10.0
        band_first = _coerce_band_first(np.asarray(array))
    elif Image is not None:
        with Image.open(path) as image:
            array = np.asarray(image)
        band_first = _coerce_band_first(array)
        pixel_size_m = 10.0
    else:  # pragma: no cover - only reachable in a broken runtime
        raise RuntimeError("TIFF support requires rasterio or Pillow.")

    if band_first.ndim == 2:
        return band_first.astype(float), None, pixel_size_m

    signal = band_first[0].astype(float)
    mask = _mask_from_band(band_first[1] if band_first.shape[0] > 1 else None)
    return signal, mask, pixel_size_m


def load_chip(path: Path | str) -> tuple[np.ndarray, np.ndarray | None, float]:
    chip_path = Path(path)
    suffix = chip_path.suffix.lower()
    if suffix in {".npy", ".npz"}:
        return _load_numpy_chip(chip_path)
    if suffix in {".tif", ".tiff"}:
        return _load_tiff_chip(chip_path)
    raise ValueError(f"Unsupported chip format: {chip_path.suffix}")


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


def _prepare_signal(signal: np.ndarray, valid: np.ndarray) -> np.ndarray:
    working = np.asarray(signal, dtype=float).copy()
    if valid.any():
        fill_value = float(np.nanmean(working[valid]))
        working[~valid] = fill_value
        working -= fill_value
    else:
        working[:] = 0.0
    window = np.outer(np.hanning(working.shape[0]), np.hanning(working.shape[1]))
    return np.nan_to_num(working * window, copy=False)


def detect_swell_lines(
    chip_path: Path | str,
    *,
    noise_floor_quantile: float = 0.5,
    min_wavelength_m: float = 80.0,
    max_wavelength_m: float = 250.0,
    min_peak_snr: float = 6.0,
    min_peak_fraction: float = 0.05,
    mask_erosion_iterations: int = 2,
    min_valid_pixels: int = 512,
) -> SwellLineResult:
    signal, mask, pixel_size_m = load_chip(chip_path)
    valid = _valid_mask(signal, mask, mask_erosion_iterations)
    valid_pixel_count = int(valid.sum())

    if valid_pixel_count < min_valid_pixels:
        return SwellLineResult(
            wavelength_m=None,
            azimuth_deg=None,
            peak_power=0.0,
            classification="flat",
            peak_snr=0.0,
            peak_fraction=0.0,
            noise_floor=0.0,
            valid_pixel_count=valid_pixel_count,
            pixel_size_m=pixel_size_m,
            notes=["insufficient_valid_pixels"],
        )

    prepared = _prepare_signal(signal, valid)
    spectrum = np.fft.fftshift(np.fft.fft2(prepared))
    power = np.abs(spectrum) ** 2

    height, width = signal.shape
    fy = np.fft.fftshift(np.fft.fftfreq(height, d=pixel_size_m))
    fx = np.fft.fftshift(np.fft.fftfreq(width, d=pixel_size_m))
    fx_grid, fy_grid = np.meshgrid(fx, fy)
    radial_frequency = np.hypot(fx_grid, fy_grid)
    with np.errstate(divide="ignore", invalid="ignore"):
        wavelength_grid = np.where(radial_frequency > 0, 1.0 / radial_frequency, np.inf)

    candidate_mask = (
        np.isfinite(wavelength_grid)
        & (wavelength_grid >= min_wavelength_m)
        & (wavelength_grid <= max_wavelength_m)
    )
    candidate_power = power[candidate_mask]
    positive_candidate_power = candidate_power[candidate_power > 0]

    if positive_candidate_power.size == 0:
        return SwellLineResult(
            wavelength_m=None,
            azimuth_deg=None,
            peak_power=0.0,
            classification="flat",
            peak_snr=0.0,
            peak_fraction=0.0,
            noise_floor=0.0,
            valid_pixel_count=valid_pixel_count,
            pixel_size_m=pixel_size_m,
            notes=["no_candidate_power"],
        )

    bounded_power = np.where(candidate_mask, power, 0.0)
    peak_index = np.unravel_index(int(np.argmax(bounded_power)), bounded_power.shape)
    peak_power = float(power[peak_index])
    noise_floor = float(np.quantile(positive_candidate_power, noise_floor_quantile))
    peak_snr = peak_power / max(noise_floor, 1e-12)

    row, col = peak_index
    row_min = max(row - 1, 0)
    row_max = min(row + 2, power.shape[0])
    col_min = max(col - 1, 0)
    col_max = min(col + 2, power.shape[1])
    peak_cluster_power = float(power[row_min:row_max, col_min:col_max].sum())
    total_candidate_power = float(candidate_power.sum())
    peak_fraction = peak_cluster_power / total_candidate_power if total_candidate_power > 0 else 0.0

    wavelength_m = float(wavelength_grid[peak_index])
    azimuth_deg = float((np.degrees(np.arctan2(fx_grid[peak_index], -fy_grid[peak_index])) + 360.0) % 180.0)

    classification = (
        "organized"
        if peak_snr >= min_peak_snr and peak_fraction >= min_peak_fraction
        else "flat"
    )

    notes: list[str] = []
    if classification == "flat" and peak_snr < min_peak_snr:
        notes.append("peak_snr_below_threshold")
    if classification == "flat" and peak_fraction < min_peak_fraction:
        notes.append("peak_fraction_below_threshold")

    return SwellLineResult(
        wavelength_m=wavelength_m,
        azimuth_deg=azimuth_deg,
        peak_power=peak_power,
        classification=classification,
        peak_snr=peak_snr,
        peak_fraction=peak_fraction,
        noise_floor=noise_floor,
        valid_pixel_count=valid_pixel_count,
        pixel_size_m=pixel_size_m,
        notes=notes,
    )
