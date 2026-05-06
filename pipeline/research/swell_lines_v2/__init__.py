from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parent
RESULTS_PATH = RESEARCH_DIR / "results.json"
REPORT_PATH = RESEARCH_DIR / "REPORT.md"
PLOTS_DIR = RESEARCH_DIR / "plots"


@dataclass(frozen=True, slots=True)
class WindowPreset:
    name: str
    window_height_m: float
    window_width_m: float
    stride_m: float


WINDOW_PRESETS = {
    "bergsma": WindowPreset(
        name="bergsma",
        window_height_m=200.0,
        window_width_m=300.0,
        stride_m=50.0,
    ),
    "s2shores": WindowPreset(
        name="s2shores",
        window_height_m=800.0,
        window_width_m=800.0,
        stride_m=100.0,
    ),
}
DEFAULT_PRESET_NAME = "s2shores"


def resolve_window_preset(name: str = DEFAULT_PRESET_NAME) -> WindowPreset:
    try:
        return WINDOW_PRESETS[name]
    except KeyError as exc:  # pragma: no cover - defensive guard
        known = ", ".join(sorted(WINDOW_PRESETS))
        raise ValueError(f"Unknown window preset {name!r}. Expected one of: {known}.") from exc
