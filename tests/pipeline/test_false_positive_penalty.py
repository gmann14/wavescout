from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run_penalty(detections: list[dict]) -> float:
    payload = json.dumps(detections)
    code = f"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path({str(ROOT / 'pipeline' / 'scripts')!r})))
import importlib.util
spec = importlib.util.spec_from_file_location("rank_segments_20", Path({str(ROOT / 'pipeline' / 'scripts' / '20_rank_segments.py')!r}))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(module.compute_false_positive_penalty(json.loads({payload!r})))
"""
    result = subprocess.run(
        [str(ROOT / "venv" / "bin" / "python"), "-c", code],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return float(result.stdout.strip())


def test_false_positive_penalty_requires_repeated_flat_day_contamination() -> None:
    detections = [
        {"quality_score": 100, "foam_fraction": 0.48, "swell_height_m": 0.48},
        {"quality_score": 100, "foam_fraction": 0.23, "swell_height_m": 0.42},
        {"quality_score": 100, "foam_fraction": 0.64, "swell_height_m": 0.46},
        {"quality_score": 100, "foam_fraction": 0.07, "swell_height_m": 0.44},
        {"quality_score": 100, "foam_fraction": 0.05, "swell_height_m": 0.36},
        {"quality_score": 100, "foam_fraction": 0.06, "swell_height_m": 0.40},
        {"quality_score": 100, "foam_fraction": 0.09, "swell_height_m": 0.24},
        {"quality_score": 100, "foam_fraction": 0.08, "swell_height_m": 0.38},
        {"quality_score": 100, "foam_fraction": 0.11, "swell_height_m": 0.48},
        {"quality_score": 100, "foam_fraction": 0.10, "swell_height_m": 0.42},
        {"quality_score": 100, "foam_fraction": 0.12, "swell_height_m": 0.46},
        {"quality_score": 100, "foam_fraction": 0.08, "swell_height_m": 0.34},
        {"quality_score": 100, "foam_fraction": 0.13, "swell_height_m": 0.48},
        {"quality_score": 100, "foam_fraction": 0.09, "swell_height_m": 0.40},
        {"quality_score": 100, "foam_fraction": 0.07, "swell_height_m": 0.46},
        {"quality_score": 100, "foam_fraction": 0.06, "swell_height_m": 0.42},
        {"quality_score": 100, "foam_fraction": 0.08, "swell_height_m": 0.44},
        {"quality_score": 100, "foam_fraction": 0.07, "swell_height_m": 0.28},
        {"quality_score": 100, "foam_fraction": 0.06, "swell_height_m": 0.48},
        {"quality_score": 100, "foam_fraction": 0.07, "swell_height_m": 0.32},
    ]

    assert _run_penalty(detections) == 0.0


def test_false_positive_penalty_triggers_for_consistent_flat_day_foam() -> None:
    detections = [
        {"quality_score": 100, "foam_fraction": 0.30, "swell_height_m": 0.48},
        {"quality_score": 100, "foam_fraction": 0.25, "swell_height_m": 0.42},
        {"quality_score": 100, "foam_fraction": 0.29, "swell_height_m": 0.46},
        {"quality_score": 100, "foam_fraction": 0.07, "swell_height_m": 0.44},
        {"quality_score": 100, "foam_fraction": 0.05, "swell_height_m": 0.36},
        {"quality_score": 100, "foam_fraction": 0.06, "swell_height_m": 0.40},
        {"quality_score": 100, "foam_fraction": 0.24, "swell_height_m": 0.24},
        {"quality_score": 100, "foam_fraction": 0.23, "swell_height_m": 0.38},
        {"quality_score": 100, "foam_fraction": 0.11, "swell_height_m": 0.48},
        {"quality_score": 100, "foam_fraction": 0.10, "swell_height_m": 0.42},
    ]

    assert _run_penalty(detections) == 5.0
