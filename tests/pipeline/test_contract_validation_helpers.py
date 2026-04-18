from __future__ import annotations

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
