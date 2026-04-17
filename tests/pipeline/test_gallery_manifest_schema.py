from __future__ import annotations


def test_gallery_manifest_has_required_top_level_fields(gallery_payload: dict) -> None:
    required = {
        "run_id",
        "generated_at_utc",
        "code_version",
        "parameters",
        "spots",
        "summary",
    }
    assert required.issubset(gallery_payload)


def test_gallery_spot_entry_has_required_fields(gallery_payload: dict) -> None:
    spot = gallery_payload["spots"][0]
    assert {"spot_name", "slug", "publication_status", "scenes"}.issubset(spot)


def test_gallery_scene_entry_has_required_fields(gallery_payload: dict) -> None:
    scene = gallery_payload["spots"][0]["scenes"][0]
    required = {
        "date",
        "scene_id",
        "quality_status",
        "quality_score",
        "swell_height_m",
        "swell_period_s",
        "swell_direction_deg",
        "cloud_pct",
        "foam_fraction",
        "bin_label",
        "rgb_path",
        "nir_path",
    }
    assert required.issubset(scene)
