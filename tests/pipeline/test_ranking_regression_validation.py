from __future__ import annotations

import json
from pathlib import Path

import pipeline.scripts._ranking_support as ranking_support
from pipeline.scripts._ranking_support import (
    build_spot_neighborhood_report,
    classify_watchlist_action,
    validate_spot_neighborhood_regressions,
    validate_ranking_region_regressions,
    validate_ranking_regressions,
)


def test_validate_ranking_regressions_accepts_passing_cases(tmp_path: Path) -> None:
    regression_path = tmp_path / "ranking_regressions.json"
    regression_path.write_text(
        json.dumps(
            {
                "cases": [
                    {"name": "a", "segment_id": "seg-a", "min_score": 60},
                    {
                        "name": "b",
                        "higher_segment_id": "seg-a",
                        "lower_segment_id": "seg-b",
                        "min_margin": 10,
                    },
                ]
            }
        )
    )
    segments = {
        "seg-a": {"composite_score": 70.0},
        "seg-b": {"composite_score": 50.0},
    }

    passed, issues = validate_ranking_regressions(segments, regression_path)
    assert passed is True
    assert issues == []


def test_validate_ranking_regressions_reports_failures(tmp_path: Path) -> None:
    regression_path = tmp_path / "ranking_regressions.json"
    regression_path.write_text(
        json.dumps(
            {
                "cases": [
                    {"name": "a", "segment_id": "seg-a", "max_score": 40},
                    {
                        "name": "b",
                        "higher_segment_id": "seg-a",
                        "lower_segment_id": "seg-b",
                        "min_margin": 10,
                    },
                ]
            }
        )
    )
    segments = {
        "seg-a": {"composite_score": 45.0},
        "seg-b": {"composite_score": 40.0},
    }

    passed, issues = validate_ranking_regressions(segments, regression_path)
    assert passed is False
    assert len(issues) == 2


def test_validate_ranking_region_regressions_accepts_passing_regions(tmp_path: Path) -> None:
    regression_path = tmp_path / "ranking_region_regressions.json"
    regression_path.write_text(
        json.dumps(
            {
                "regions": [
                    {
                        "name": "sheltered",
                        "bbox": [0, 0, 10, 10],
                        "max_score": 40,
                        "max_count_ge_50": 0,
                    },
                    {
                        "name": "open",
                        "bbox": [20, 20, 30, 30],
                        "min_score": 75,
                        "min_count_ge_70": 1,
                    },
                ]
            }
        )
    )
    features = [
        {
            "geometry": {"type": "LineString", "coordinates": [[1, 1], [2, 2]]},
            "properties": {"segment_id": "seg-a", "composite_score": 35.0},
        },
        {
            "geometry": {"type": "LineString", "coordinates": [[21, 21], [22, 22]]},
            "properties": {"segment_id": "seg-b", "composite_score": 80.0},
        },
    ]

    passed, issues, summaries = validate_ranking_region_regressions(features, regression_path)
    assert passed is True
    assert issues == []
    assert len(summaries) == 2


def test_validate_ranking_region_regressions_reports_failures(tmp_path: Path) -> None:
    regression_path = tmp_path / "ranking_region_regressions.json"
    regression_path.write_text(
        json.dumps(
            {
                "regions": [
                    {
                        "name": "sheltered",
                        "bbox": [0, 0, 10, 10],
                        "max_score": 40,
                        "max_count_ge_50": 0,
                    },
                    {
                        "name": "open",
                        "bbox": [20, 20, 30, 30],
                        "min_score": 75,
                        "min_count_ge_70": 1,
                    },
                ]
            }
        )
    )
    features = [
        {
            "geometry": {"type": "LineString", "coordinates": [[1, 1], [2, 2]]},
            "properties": {"segment_id": "seg-a", "composite_score": 55.0},
        },
        {
            "geometry": {"type": "LineString", "coordinates": [[21, 21], [22, 22]]},
            "properties": {"segment_id": "seg-b", "composite_score": 60.0},
        },
    ]

    passed, issues, _ = validate_ranking_region_regressions(features, regression_path)
    assert passed is False
    assert len(issues) == 4


def test_validate_spot_neighborhood_regressions_accepts_passing_cases(tmp_path: Path) -> None:
    spots_path = tmp_path / "ns_spots.geojson"
    spots_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"slug": "spot-a"},
                        "geometry": {"type": "Point", "coordinates": [-63.0, 44.0]},
                    }
                ],
            }
        )
    )
    regression_path = tmp_path / "spot_neighborhood_regressions.json"
    regression_path.write_text(
        json.dumps(
            {
                "spots": [
                    {
                        "slug": "spot-a",
                        "radius_m": 2500,
                        "within_distance_m": 1000,
                        "min_best_score_within_distance": 70,
                        "min_best_score": 70,
                        "min_count_ge_60": 1,
                    }
                ]
            }
        )
    )
    features = [
        {
            "geometry": {"type": "LineString", "coordinates": [[-63.0, 44.0], [-63.001, 44.001]]},
            "properties": {"segment_id": "seg-a", "composite_score": 75.0},
        }
    ]

    passed, issues, summaries = validate_spot_neighborhood_regressions(features, spots_path, regression_path)
    assert passed is True
    assert issues == []
    assert len(summaries) == 1


def test_validate_spot_neighborhood_regressions_reports_failures(tmp_path: Path) -> None:
    spots_path = tmp_path / "ns_spots.geojson"
    spots_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"slug": "spot-a"},
                        "geometry": {"type": "Point", "coordinates": [-63.0, 44.0]},
                    }
                ],
            }
        )
    )
    regression_path = tmp_path / "spot_neighborhood_regressions.json"
    regression_path.write_text(
        json.dumps(
            {
                "spots": [
                    {
                        "slug": "spot-a",
                        "radius_m": 2500,
                        "min_best_score": 70,
                        "min_count_ge_60": 1,
                        "min_count_ge_70": 1,
                    }
                ]
            }
        )
    )
    features = [
        {
            "geometry": {"type": "LineString", "coordinates": [[-63.0, 44.0], [-63.001, 44.001]]},
            "properties": {"segment_id": "seg-a", "composite_score": 65.0},
        }
    ]

    passed, issues, _ = validate_spot_neighborhood_regressions(features, spots_path, regression_path)
    assert passed is False
    assert len(issues) == 2


def test_build_spot_neighborhood_report_uses_current_coordinates(tmp_path: Path) -> None:
    spots_payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "slug": "spot-a",
                    "name": "Spot A",
                    "source": "well-known",
                    "swell_window": "S/SE",
                },
                "geometry": {"type": "Point", "coordinates": [-63.0, 44.0]},
            },
            {
                "type": "Feature",
                "properties": {
                    "slug": "internal-a",
                    "name": "Internal A",
                    "source": "graham-local-knowledge",
                },
                "geometry": {"type": "Point", "coordinates": [-63.0, 44.0]},
            },
        ],
    }
    regression_payload = {
        "spots": [
            {
                "slug": "spot-a",
                "radius_m": 2500,
                "within_distance_m": 1000,
                "min_best_score_within_distance": 70,
                "min_best_score": 70,
            }
        ]
    }
    features = [
        {
            "geometry": {"type": "LineString", "coordinates": [[-63.0, 44.0], [-63.001, 44.001]]},
            "properties": {"segment_id": "seg-a", "composite_score": 75.0, "orientation_deg": 170.0},
        }
    ]

    report = build_spot_neighborhood_report(features, spots_payload, regression_payload)
    assert report["summary"]["trusted_spot_count"] == 1
    assert report["summary"]["spots_meeting_expectations"] == 1
    assert len(report["spot_neighborhoods"]) == 1
    assert report["spot_neighborhoods"][0]["slug"] == "spot-a"
    assert report["spot_neighborhoods"][0]["best_segment_id"] == "seg-a"
    assert report["spot_neighborhoods"][0]["best_score_within_distance"] == 75.0
    assert report["spot_neighborhoods"][0]["follow_up_action"] == "none"
    assert report["summary"]["follow_up_counts"]["coordinate_or_source_review"] == 0


def test_build_spot_neighborhood_report_passes_without_local_window_requirement(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "spot-a.json").write_text(
        json.dumps(
            {
                "slug": "spot-a",
                "point": {"lon": -63.0, "lat": 44.0},
            }
        )
    )
    monkeypatch.setattr(ranking_support, "CONFIGS_DIR", config_dir)

    spots_payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "slug": "spot-a",
                    "name": "Spot A",
                    "source": "well-known",
                },
                "geometry": {"type": "Point", "coordinates": [-63.0, 44.0]},
            }
        ],
    }
    regression_payload = {
        "spots": [
            {
                "slug": "spot-a",
                "radius_m": 2500,
                "min_best_score": 58.0,
            }
        ]
    }
    features = [
        {
            "geometry": {"type": "LineString", "coordinates": [[-63.01, 44.01], [-63.011, 44.011]]},
            "properties": {"segment_id": "seg-a", "composite_score": 61.0, "orientation_deg": 170.0},
        }
    ]

    report = build_spot_neighborhood_report(features, spots_payload, regression_payload)
    item = report["spot_neighborhoods"][0]
    assert item["meets_expectations"] is True
    assert item["best_score_within_distance"] is None
    assert item["follow_up_action"] == "none"
    assert report["summary"]["follow_up_counts"]["spot_definition_review"] == 0


def test_build_spot_neighborhood_report_flags_coordinate_review_when_only_broad_support_exists() -> None:
    spots_payload = {
        "type": "FeatureCollection",
        "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "slug": "spot-a",
                        "name": "Spot A",
                        "source": "well-known",
                    },
                    "geometry": {"type": "Point", "coordinates": [-63.004, 44.004]},
                }
            ],
        }
    regression_payload = {
        "spots": [
            {
                "slug": "spot-a",
                "radius_m": 2500,
                "within_distance_m": 200,
                "min_best_score": 70,
            }
        ]
    }
    features = [
        {
            "geometry": {"type": "LineString", "coordinates": [[-63.01, 44.01], [-63.011, 44.011]]},
            "properties": {"segment_id": "seg-a", "composite_score": 75.0, "orientation_deg": 170.0},
        }
    ]

    report = build_spot_neighborhood_report(features, spots_payload, regression_payload)
    assert report["spot_neighborhoods"][0]["meets_expectations"] is True
    assert report["spot_neighborhoods"][0]["best_score_within_distance"] is None
    assert report["spot_neighborhoods"][0]["follow_up_action"] == "coordinate_or_source_review"
    assert report["summary"]["follow_up_counts"]["coordinate_or_source_review"] == 1


def test_build_spot_neighborhood_report_flags_spot_definition_review_when_config_aligned(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "spot-a.json").write_text(
        json.dumps(
            {
                "slug": "spot-a",
                "point": {"lon": -63.0, "lat": 44.0},
            }
        )
    )
    monkeypatch.setattr(ranking_support, "CONFIGS_DIR", config_dir)

    spots_payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "slug": "spot-a",
                    "name": "Spot A",
                    "source": "well-known",
                },
                "geometry": {"type": "Point", "coordinates": [-63.0, 44.0]},
            }
        ],
    }
    regression_payload = {
        "spots": [
            {
                "slug": "spot-a",
                "radius_m": 2500,
                "within_distance_m": 200,
                "min_best_score": 70,
            }
        ]
    }
    features = [
        {
            "geometry": {"type": "LineString", "coordinates": [[-63.01, 44.01], [-63.011, 44.011]]},
            "properties": {"segment_id": "seg-a", "composite_score": 75.0, "orientation_deg": 170.0},
        }
    ]

    report = build_spot_neighborhood_report(features, spots_payload, regression_payload)
    assert report["spot_neighborhoods"][0]["best_score_within_distance"] is None
    assert report["spot_neighborhoods"][0]["point_to_config_distance_m"] == 0.0
    assert report["spot_neighborhoods"][0]["follow_up_action"] == "spot_definition_review"
    assert report["summary"]["follow_up_counts"]["spot_definition_review"] == 1


def test_build_spot_neighborhood_report_prefers_best_config_break_anchor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "spot-a.json").write_text(
        json.dumps(
            {
                "slug": "spot-a",
                "point": {"lon": -63.0, "lat": 44.0},
                "breaks": [
                    {"name": "Outer", "lon": -63.01, "lat": 44.01},
                    {"name": "Inner", "lon": -63.0004, "lat": 44.0004},
                ],
            }
        )
    )
    monkeypatch.setattr(ranking_support, "CONFIGS_DIR", config_dir)

    spots_payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "slug": "spot-a",
                    "name": "Spot A",
                    "source": "well-known",
                },
                "geometry": {"type": "Point", "coordinates": [-63.004, 44.004]},
            }
        ],
    }
    regression_payload = {
        "spots": [
            {
                "slug": "spot-a",
                "radius_m": 2500,
                "within_distance_m": 200,
                "min_best_score_within_distance": 70,
            }
        ]
    }
    features = [
        {
            "geometry": {"type": "LineString", "coordinates": [[-63.01, 44.01], [-63.011, 44.011]]},
            "properties": {"segment_id": "seg-outer", "composite_score": 68.0, "orientation_deg": 170.0},
        },
        {
            "geometry": {"type": "LineString", "coordinates": [[-63.0005, 44.0005], [-63.0006, 44.0006]]},
            "properties": {"segment_id": "seg-inner", "composite_score": 75.0, "orientation_deg": 175.0},
        },
    ]

    report = build_spot_neighborhood_report(features, spots_payload, regression_payload)
    item = report["spot_neighborhoods"][0]
    assert item["selected_anchor_name"] == "Inner"
    assert item["best_segment_id"] == "seg-inner"
    assert item["best_score_within_distance"] == 75.0


def test_build_spot_neighborhood_report_flags_evidence_limited_ranking_review(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "spot-a.json").write_text(
        json.dumps(
            {
                "slug": "spot-a",
                "point": {"lon": -63.0, "lat": 44.0},
            }
        )
    )
    monkeypatch.setattr(ranking_support, "CONFIGS_DIR", config_dir)

    spots_payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "slug": "spot-a",
                    "name": "Spot A",
                    "source": "well-known",
                },
                "geometry": {"type": "Point", "coordinates": [-63.0, 44.0]},
            }
        ],
    }
    regression_payload = {
        "spots": [
            {
                "slug": "spot-a",
                "radius_m": 2500,
                "min_best_score": 75,
            }
        ]
    }
    features = [
        {
            "geometry": {"type": "LineString", "coordinates": [[-63.0, 44.0], [-63.001, 44.001]]},
            "properties": {
                "segment_id": "seg-a",
                "composite_score": 66.7,
                "orientation_deg": 170.0,
                "confidence": 2,
                "evidence_sparsity_penalty": 4.0,
                "false_positive_penalty": 0.0,
                "coastal_context_penalty": 0.0,
                "geometry_component": 26.0,
                "foam_component": 30.0,
                "profile_component": 0.0,
            },
        }
    ]

    report = build_spot_neighborhood_report(features, spots_payload, regression_payload)
    item = report["spot_neighborhoods"][0]
    assert item["meets_expectations"] is False
    assert item["follow_up_action"] == "ranking_review"
    assert "no swell-profile coverage" in item["follow_up_reason"]
    assert item["best_segment_confidence"] == 2
    assert item["best_segment_evidence_sparsity_penalty"] == 4.0


def test_build_spot_neighborhood_report_flags_profile_coverage_gap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "spot-a.json").write_text(
        json.dumps(
            {
                "slug": "spot-a",
                "point": {"lon": -63.0, "lat": 44.0},
            }
        )
    )
    monkeypatch.setattr(ranking_support, "CONFIGS_DIR", config_dir)

    spots_payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "slug": "spot-a",
                    "name": "Spot A",
                    "source": "well-known",
                },
                "geometry": {"type": "Point", "coordinates": [-63.0, 44.0]},
            }
        ],
    }
    regression_payload = {
        "spots": [
            {
                "slug": "spot-a",
                "radius_m": 2500,
                "min_best_score": 75,
            }
        ]
    }
    features = [
        {
            "geometry": {"type": "LineString", "coordinates": [[-63.0, 44.0], [-63.001, 44.001]]},
            "properties": {
                "segment_id": "seg-a",
                "composite_score": 71.7,
                "orientation_deg": 170.0,
                "confidence": 2,
                "evidence_sparsity_penalty": 4.0,
                "false_positive_penalty": 0.0,
                "coastal_context_penalty": 0.0,
                "geometry_component": 26.0,
                "foam_component": 30.0,
                "profile_component": 0.0,
            },
        }
    ]

    report = build_spot_neighborhood_report(features, spots_payload, regression_payload)
    item = report["spot_neighborhoods"][0]
    assert item["meets_expectations"] is False
    assert item["follow_up_action"] == "ranking_review"
    assert "no swell-profile coverage" in item["follow_up_reason"]
    assert item["best_segment_profile_component"] == 0.0


def test_classify_watchlist_action_promotes_close_high_trust_spot() -> None:
    action, reason = classify_watchlist_action(
        {
            "slug": "right-point",
            "spot_source": "surfline",
            "best_segment_score": 78.3,
            "best_score_within_distance": 78.3,
            "best_segment_distance_m": 255.9,
            "config_point_lon": -63.25684,
        },
        tracked_slugs=set(),
    )

    assert action == "priority_regression_candidate"
    assert "Trusted public source" in reason


def test_classify_watchlist_action_flags_far_high_trust_spot_for_coordinate_review() -> None:
    action, reason = classify_watchlist_action(
        {
            "slug": "osbourne",
            "spot_source": "surfline",
            "best_segment_score": 61.9,
            "best_score_within_distance": 39.7,
            "best_segment_distance_m": 2022.7,
            "config_point_lon": -63.417,
        },
        tracked_slugs=set(),
    )

    assert action == "coordinate_review_candidate"
    assert "too far" in reason


def test_classify_watchlist_action_promotes_far_high_trust_spot_with_strong_local_support() -> None:
    action, reason = classify_watchlist_action(
        {
            "slug": "left-point",
            "spot_source": "surfline",
            "best_segment_score": 84.7,
            "best_score_within_distance": 83.0,
            "best_segment_distance_m": 2277.7,
            "config_point_lon": -63.325,
        },
        tracked_slugs=set(),
    )

    assert action == "priority_regression_candidate"
    assert "strong local ranked support" in reason


def test_classify_watchlist_action_keeps_alternate_break_anchor_as_research_candidate() -> None:
    action, reason = classify_watchlist_action(
        {
            "slug": "osbourne",
            "spot_name": "Osbourne",
            "spot_source": "surfline",
            "best_segment_score": 61.9,
            "best_score_within_distance": 61.9,
            "best_segment_distance_m": 779.5,
            "config_point_lon": -63.417,
            "selected_anchor_source": "config-break",
            "selected_anchor_name": "The Moose",
        },
        tracked_slugs=set(),
    )

    assert action == "research_candidate"
    assert "different break anchor" in reason


def test_classify_watchlist_action_marks_broad_wannasurf_label_as_research() -> None:
    action, reason = classify_watchlist_action(
        {
            "slug": "fishermans-reserve",
            "spot_name": "Fisherman's Reserve",
            "spot_source": "wannasurf",
            "best_segment_score": 78.3,
            "best_score_within_distance": 62.2,
            "best_segment_distance_m": 1531.6,
        },
        tracked_slugs=set(),
    )

    assert action == "research_candidate"
    assert "Strong broad support exists" in reason
