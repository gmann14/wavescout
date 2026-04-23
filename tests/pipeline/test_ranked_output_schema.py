from __future__ import annotations


def test_spots_payload_uses_normalized_fields(spots_payload: dict) -> None:
    assert spots_payload["type"] == "FeatureCollection"
    feature = spots_payload["features"][0]
    props = feature["properties"]

    required = {
        "name",
        "slug",
        "break_type",
        "verification_status",
        "publication_status",
        "surf_potential_score",
        "evidence_confidence_level",
        "evidence_confidence_label",
        "gallery_available",
        "swell_profile_available",
        "quality_status",
        "foam_summary",
        "explanation",
    }

    assert required.issubset(props)
    assert "confidence" not in props


def test_high_segments_payload_uses_candidate_contract(segments_high_payload: dict) -> None:
    assert segments_high_payload["type"] == "FeatureCollection"
    feature = segments_high_payload["features"][0]
    props = feature["properties"]

    required = {
        "id",
        "verification_status",
        "publication_status",
        "map_display_eligible",
        "surf_potential_score",
        "evidence_confidence_level",
        "evidence_confidence_label",
        "quality_status",
        "coastal_exposure_class",
        "coastal_context_penalty",
        "evidence_sparsity_penalty",
        "nearfield_open_water_deg",
        "nearfield_blocked_ratio",
        "farfield_open_water_deg",
        "farfield_blocked_ratio",
        "score_components",
        "foam_obs_count",
        "turn_on_threshold_m",
        "optimal_swell_range",
        "primary_direction",
        "explanation",
    }

    assert required.issubset(props)
    assert props["verification_status"] == "candidate"
    assert props["publication_status"] == "public_coarse"
    assert isinstance(props["map_display_eligible"], bool)
