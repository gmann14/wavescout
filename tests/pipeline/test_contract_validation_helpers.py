from __future__ import annotations

from copy import deepcopy

import pytest

from pipeline.scripts._public_dataset import (
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
