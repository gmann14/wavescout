from __future__ import annotations

from pipeline.scripts._ranking_support import evidence_sparsity_penalty, trusted_calibration_match


def test_evidence_sparsity_penalty_prefers_corrobated_segments() -> None:
    assert evidence_sparsity_penalty(1) == 12.0
    assert evidence_sparsity_penalty(2) == 4.0
    assert evidence_sparsity_penalty(3) == 0.0


def test_trusted_calibration_match_filters_stale_or_misaligned_matches() -> None:
    assert trusted_calibration_match(900.0, "SE", 140.0) is True
    assert trusted_calibration_match(3000.0, "SE", 140.0) is False
    assert trusted_calibration_match(900.0, "SE", 236.0) is False
