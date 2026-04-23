from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "pipeline" / "scripts" / "15_generate_gallery_images.py"
sys.path.insert(0, str(SCRIPT_PATH.parent))
sys.modules.setdefault("ee", types.SimpleNamespace())
sys.modules.setdefault("requests", types.SimpleNamespace())
sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None))
SPEC = importlib.util.spec_from_file_location("gallery_images", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
gallery_images = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gallery_images)
pick_representative_scenes = gallery_images.pick_representative_scenes
selection_defaults = gallery_images.selection_defaults
output_manifest_name = gallery_images.output_manifest_name


def test_pick_representative_scenes_can_return_multiple_per_bin() -> None:
    scenes = {
        "2024-01-01": {
            "swell_height_m": 1.3,
            "swell_period_s": 10.0,
            "quality_score": 92.0,
            "median_foam_fraction": 0.30,
            "wave_energy": 10.0,
            "valid_segments": 4,
        },
        "2024-01-15": {
            "swell_height_m": 1.4,
            "swell_period_s": 9.0,
            "quality_score": 91.0,
            "median_foam_fraction": 0.25,
            "wave_energy": 9.0,
            "valid_segments": 4,
        },
        "2024-02-01": {
            "swell_height_m": 2.0,
            "swell_period_s": 11.0,
            "quality_score": 95.0,
            "median_foam_fraction": 0.35,
            "wave_energy": 14.0,
            "valid_segments": 5,
        },
    }

    picks = pick_representative_scenes(
        scenes,
        max_scenes_per_bin=2,
        min_gallery_qs=90.0,
        min_period_s=8.0,
    )

    moderate = [p for p in picks if p["bin_label"] == "moderate"]
    big = [p for p in picks if p["bin_label"] == "big"]
    assert len(moderate) == 2
    assert len(big) == 1
    assert moderate[0]["date"] == "2024-01-01"
    assert moderate[1]["date"] == "2024-01-15"


def test_pick_representative_scenes_respects_relaxed_quality_threshold() -> None:
    scenes = {
        "2024-03-01": {
            "swell_height_m": 1.0,
            "swell_period_s": 7.0,
            "quality_score": 82.0,
            "median_foam_fraction": 0.22,
            "wave_energy": 7.0,
            "valid_segments": 3,
        },
        "2024-03-05": {
            "swell_height_m": 1.0,
            "swell_period_s": 9.0,
            "quality_score": 76.0,
            "median_foam_fraction": 0.28,
            "wave_energy": 8.0,
            "valid_segments": 3,
        },
    }

    default_picks = pick_representative_scenes(scenes)
    relaxed_picks = pick_representative_scenes(
        scenes,
        min_gallery_qs=75.0,
        min_period_s=6.0,
        max_scenes_per_bin=2,
    )

    assert len(default_picks) == 0
    assert len(relaxed_picks) == 2


def test_reference_bank_defaults_are_relaxed_but_explicit() -> None:
    public_defaults = selection_defaults(reference_bank=False)
    reference_defaults = selection_defaults(reference_bank=True)

    assert public_defaults == {
        "min_gallery_qs": 90,
        "min_period_s": 8.0,
        "max_scenes_per_bin": 1,
    }
    assert reference_defaults == {
        "min_gallery_qs": 75.0,
        "min_period_s": 6.0,
        "max_scenes_per_bin": 3,
    }


def test_reference_bank_manifest_name_is_not_public_manifest() -> None:
    assert output_manifest_name(reference_bank=False) == "manifest.json"
    assert output_manifest_name(reference_bank=True) == "reference-bank-manifest.json"
