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
        "surf_potential_score",
        "evidence_confidence_level",
        "evidence_confidence_label",
        "quality_status",
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
