from __future__ import annotations

from copy import deepcopy

import pytest

from pipeline.scripts._public_dataset import (
    derive_spot_verification_status,
    map_display_eligible_for_segment,
    validate_dataset_manifest,
    validate_gallery_payload,
    validate_segments_high_payload,
    validate_spots_payload,
)


def test_validation_helpers_accept_strict_fixtures(
    dataset_manifest: dict,
    spots_payload: dict,
    segments_high_payload: dict,
    gallery_payload: dict,
) -> None:
    validate_dataset_manifest(dataset_manifest)
    validate_spots_payload(spots_payload, strict=True)
    validate_segments_high_payload(segments_high_payload, strict=True)
    validate_gallery_payload(gallery_payload, strict=True)


def test_spots_validator_rejects_internal_only_leaks(spots_payload: dict) -> None:
    leaked = deepcopy(spots_payload)
    leaked["features"][0]["properties"]["publication_status"] = "internal_only"

    with pytest.raises(ValueError, match="must not expose internal_only spots"):
        validate_spots_payload(leaked, strict=False)


def test_gallery_validator_rejects_internal_only_leaks(gallery_payload: dict) -> None:
    leaked = deepcopy(gallery_payload)
    leaked["spots"][0]["publication_status"] = "internal_only"

    with pytest.raises(ValueError, match="must not expose internal_only spots"):
        validate_gallery_payload(leaked, strict=False)


def test_segment_map_display_gate_requires_moderate_evidence() -> None:
    assert map_display_eligible_for_segment(2, "public_coarse", 170.0, 100.0, 110.0, 130.0) is True
    assert map_display_eligible_for_segment(3, "public_coarse", 140.0, 120.0, 120.0, 130.0) is True
    assert map_display_eligible_for_segment(1, "public_coarse", 170.0, 100.0, 110.0, 130.0) is False
    assert map_display_eligible_for_segment(None, "public_coarse", 170.0, 100.0, 110.0, 130.0) is False
    assert map_display_eligible_for_segment(2, "internal_only", 170.0, 100.0, 110.0, 130.0) is False
    assert map_display_eligible_for_segment(2, "public_coarse", 95.0, 100.0, 110.0, 130.0) is False
    assert map_display_eligible_for_segment(2, "public_coarse", 170.0, 80.0, 110.0, 130.0) is False
    assert map_display_eligible_for_segment(2, "public_coarse", 170.0, 100.0, 80.0, 130.0) is False
    assert map_display_eligible_for_segment(2, "public_coarse", 170.0, 100.0, 90.0, 130.0) is False


def test_named_spot_sources_serialize_as_confirmed_reference_entries() -> None:
    assert derive_spot_verification_status("well-known", None) == "confirmed"
    assert derive_spot_verification_status("public-nomadsurfers", "low") == "confirmed"
    assert derive_spot_verification_status("graham-local-knowledge", "high") == "confirmed"


def test_segments_high_validator_rejects_full_precision_public_coarse_coordinates(
    segments_high_payload: dict,
) -> None:
    leaked = deepcopy(segments_high_payload)
    leaked["features"][0]["geometry"]["coordinates"] = [-63.353809, 44.641669]

    with pytest.raises(ValueError, match="rounded to 3 decimals max"):
        validate_segments_high_payload(leaked, strict=True)


def test_segments_high_validator_rejects_legacy_confidence_field(
    segments_high_payload: dict,
) -> None:
    leaked = deepcopy(segments_high_payload)
    leaked["features"][0]["properties"]["confidence"] = "high"

    with pytest.raises(ValueError, match="must not expose legacy confidence"):
        validate_segments_high_payload(leaked, strict=True)
