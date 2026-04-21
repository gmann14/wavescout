from __future__ import annotations

from pipeline.scripts._coastal_context import (
    coastal_context_penalty,
    coastal_exposure_class,
    is_primary_swell_facing,
)


def test_primary_swell_facing_window_matches_public_gate() -> None:
    assert is_primary_swell_facing(170.0) is True
    assert is_primary_swell_facing(120.0) is True
    assert is_primary_swell_facing(220.0) is True
    assert is_primary_swell_facing(95.0) is False
    assert is_primary_swell_facing(265.0) is False


def test_coastal_exposure_class_bins_exposure_arc() -> None:
    assert coastal_exposure_class(140.0) == "open_coast"
    assert coastal_exposure_class(100.0) == "outer_coast"
    assert coastal_exposure_class(75.0) == "semi_sheltered"
    assert coastal_exposure_class(45.0) == "sheltered_inner_coast"


def test_coastal_context_penalty_hits_sheltered_or_misaligned_segments() -> None:
    assert coastal_context_penalty(150.0, 170.0, 130.0, 0.0, 130.0, 0.0) == 0.0
    assert coastal_context_penalty(100.0, 170.0, 130.0, 0.0, 130.0, 0.0) == 8.0
    assert coastal_context_penalty(75.0, 170.0, 100.0, 0.23, 80.0, 0.35) == 28.0
    assert coastal_context_penalty(45.0, 170.0, 80.0, 0.4, 50.0, 0.6) == 28.0
    assert coastal_context_penalty(100.0, 260.0, 130.0, 0.0, 130.0, 0.0) == 18.0


def test_coastal_context_penalty_catches_deep_bay_false_opens() -> None:
    assert coastal_context_penalty(140.0, 170.0, 130.0, 0.0, 60.0, 0.5) == 28.0
    assert coastal_context_penalty(140.0, 170.0, 130.0, 0.0, 110.0, 0.0) == 0.0
