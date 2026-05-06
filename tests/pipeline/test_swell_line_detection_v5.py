from __future__ import annotations

from pathlib import Path

from pipeline.research.swell_lines_v5.signal_validation import (
    build_candidate_scenes,
    build_scene_catalog,
    build_summary,
    load_scene_reviews,
    write_json,
    write_review_template,
)


def test_build_scene_catalog_uses_foam_manifests_and_merges_gallery_paths(tmp_path: Path) -> None:
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    gallery_manifest_path = tmp_path / "gallery.json"

    write_json(
        manifests_dir / "demo_foam_detections.json",
        {
            "scene_quality": [
                {"date": "2026-01-01", "cloud_pct": 2.0, "quality_score": 95.0, "valid_pct": 99.0},
                {"date": "2026-01-02", "cloud_pct": 1.0, "quality_score": 93.0, "valid_pct": 98.0},
            ],
            "detections": [
                {"date": "2026-01-01", "segment_id": "a", "swell_height_m": 2.1, "swell_period_s": 9.0, "swell_direction_deg": 120},
                {"date": "2026-01-02", "segment_id": "a", "swell_height_m": 1.8, "swell_period_s": 8.3, "swell_direction_deg": 125},
            ],
        },
    )
    write_json(
        gallery_manifest_path,
        {
            "spots": [
                {
                    "spot_name": "Demo",
                    "slug": "demo",
                    "scenes": [
                        {
                            "date": "2026-01-01",
                            "rgb_path": "gallery/demo_2026-01-01_rgb.png",
                            "nir_path": "gallery/demo_2026-01-01_nir.png",
                        }
                    ],
                }
            ]
        },
    )
    pairs_path = tmp_path / "pairs.json"
    write_json(
        pairs_path,
        {
            "pairs": [
                {
                    "spot_name": "Demo",
                    "slug": "demo",
                    "config_path": "pipeline/configs/demo.json",
                    "bbox": [0, 1, 2, 3],
                    "window_bbox": [0, 1, 2, 3],
                    "organized_scene": {"date": "2026-01-01"},
                    "flat_scene": {"date": "2026-01-10"},
                }
            ]
        },
    )

    payload = build_scene_catalog(
        pairs_path=pairs_path,
        manifests_dir=manifests_dir,
        gallery_manifest_path=gallery_manifest_path,
        refresh_recent=False,
    )

    assert payload["summary"]["scene_count"] == 2
    assert payload["spots"][0]["local_scene_count"] == 2
    assert payload["spots"][0]["scenes"][0]["rgb_path"] == "gallery/demo_2026-01-01_rgb.png"
    assert payload["spots"][0]["scenes"][1]["scene_source"] == "foam_manifest"


def test_build_candidate_scenes_uses_catalog_and_records_shortfall(tmp_path: Path) -> None:
    scene_catalog = {
        "summary": {"scene_count": 2},
        "spots": [
            {
                "spot_slug": "demo",
                "spot_name": "Demo",
                "scenes": [
                    {
                        "date": "2026-01-01",
                        "scene_source": "foam_manifest",
                        "config_path": "pipeline/configs/demo.json",
                        "bbox": [0, 1, 2, 3],
                        "window_bbox": [0, 1, 2, 3],
                        "swell_height_m": 2.1,
                        "swell_period_s": 9.0,
                        "cloud_pct": 2.0,
                        "quality_score": 95.0,
                        "wave_energy": 12.0,
                    },
                    {
                        "date": "2026-01-02",
                        "scene_source": "foam_manifest",
                        "config_path": "pipeline/configs/demo.json",
                        "bbox": [0, 1, 2, 3],
                        "window_bbox": [0, 1, 2, 3],
                        "swell_height_m": 1.8,
                        "swell_period_s": 8.3,
                        "cloud_pct": 1.0,
                        "quality_score": 94.0,
                        "wave_energy": 10.0,
                    },
                ],
            }
        ],
    }
    pairs_path = tmp_path / "pairs.json"
    write_json(
        pairs_path,
        {
            "pairs": [
                {
                    "spot_name": "Demo",
                    "slug": "demo",
                    "config_path": "pipeline/configs/demo.json",
                    "bbox": [0, 1, 2, 3],
                    "window_bbox": [0, 1, 2, 3],
                    "organized_scene": {"date": "2026-01-01"},
                    "flat_scene": {"date": "2026-01-10"},
                }
            ]
        },
    )

    payload = build_candidate_scenes(
        scene_catalog=scene_catalog,
        pairs_path=pairs_path,
        profile="strict",
        max_additional_per_spot=5,
    )

    assert payload["summary"]["selected_scene_count"] == 2
    assert payload["summary"]["shortfall"] == 4
    assert payload["candidates"][0]["source"] == "frozen_organized"
    assert payload["candidates"][1]["scene_source"] == "foam_manifest"


def test_build_candidate_scenes_ranks_additional_candidates_by_energy_then_quality(tmp_path: Path) -> None:
    scene_catalog = {
        "summary": {"scene_count": 4},
        "spots": [
            {
                "spot_slug": "demo",
                "spot_name": "Demo",
                "scenes": [
                    {"date": "2026-01-01", "scene_source": "foam_manifest", "config_path": "pipeline/configs/demo.json", "bbox": [0, 1, 2, 3], "window_bbox": [0, 1, 2, 3], "swell_height_m": 2.0, "swell_period_s": 9.0, "cloud_pct": 1.0, "quality_score": 95.0, "wave_energy": 10.0},
                    {"date": "2026-01-02", "scene_source": "foam_manifest", "config_path": "pipeline/configs/demo.json", "bbox": [0, 1, 2, 3], "window_bbox": [0, 1, 2, 3], "swell_height_m": 1.7, "swell_period_s": 8.2, "cloud_pct": 1.0, "quality_score": 93.0, "wave_energy": 13.0},
                    {"date": "2026-01-03", "scene_source": "foam_manifest", "config_path": "pipeline/configs/demo.json", "bbox": [0, 1, 2, 3], "window_bbox": [0, 1, 2, 3], "swell_height_m": 1.7, "swell_period_s": 8.2, "cloud_pct": 1.0, "quality_score": 97.0, "wave_energy": 11.0},
                    {"date": "2026-01-04", "scene_source": "foam_manifest", "config_path": "pipeline/configs/demo.json", "bbox": [0, 1, 2, 3], "window_bbox": [0, 1, 2, 3], "swell_height_m": 1.7, "swell_period_s": 8.2, "cloud_pct": 1.0, "quality_score": 91.0, "wave_energy": 9.0},
                ],
            }
        ],
    }
    pairs_path = tmp_path / "pairs.json"
    write_json(
        pairs_path,
        {
            "pairs": [
                {
                    "spot_name": "Demo",
                    "slug": "demo",
                    "config_path": "pipeline/configs/demo.json",
                    "bbox": [0, 1, 2, 3],
                    "window_bbox": [0, 1, 2, 3],
                    "organized_scene": {"date": "2026-01-01"},
                    "flat_scene": {"date": "2026-01-10"},
                }
            ]
        },
    )

    payload = build_candidate_scenes(
        scene_catalog=scene_catalog,
        pairs_path=pairs_path,
        profile="strict",
        max_additional_per_spot=2,
    )

    assert [candidate["date"] for candidate in payload["candidates"]] == [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
    ]


def test_write_review_template_preserves_existing_labels(tmp_path: Path) -> None:
    candidates_payload = {
        "candidates": [
            {
                "review_id": "demo_2026-01-01",
                "spot_slug": "demo",
                "spot_name": "Demo",
                "date": "2026-01-01",
                "source": "frozen_organized",
                "scene_source": "foam_manifest",
                "is_frozen_organized": True,
                "rgb_path": "a.png",
                "annotated_rgb_path": "a_annotated.png",
                "nir_path": "a_nir.png",
                "annotated_nir_path": "a_nir_annotated.png",
            }
        ]
    }
    reviews_path = tmp_path / "scene_reviews.csv"
    reviews_path.write_text(
        "review_id,spot_slug,spot_name,date,source,scene_source,is_frozen_organized,label,note,rgb_path,annotated_rgb_path,nir_path,annotated_nir_path\n"
        "demo_2026-01-01,demo,Demo,2026-01-01,frozen_organized,foam_manifest,true,clear_positive,looks good,a.png,a_annotated.png,a_nir.png,a_nir_annotated.png\n"
    )

    write_review_template(candidates_payload, reviews_path=reviews_path)
    rows = load_scene_reviews(reviews_path)

    assert rows[0]["label"] == "clear_positive"
    assert rows[0]["note"] == "looks good"


def test_build_summary_returns_pending_until_all_labels_exist() -> None:
    candidates_payload = {
        "candidates": [
            {"review_id": "a", "source": "frozen_organized"},
            {"review_id": "b", "source": "development_candidate"},
        ]
    }
    review_rows = [
        {"review_id": "a", "source": "frozen_organized", "label": "clear_positive"},
        {"review_id": "b", "source": "development_candidate", "label": ""},
    ]

    summary = build_summary(candidates_payload, review_rows)

    assert summary["decision"] == "pending_manual_review"
    assert summary["pending_scene_count"] == 1


def test_build_summary_routes_continue_optical_detector_research() -> None:
    candidates_payload = {
        "candidates": [
            {"review_id": str(i), "source": "frozen_organized" if i < 4 else "development_candidate"}
            for i in range(10)
        ]
    }
    review_rows = [
        {"review_id": "0", "source": "frozen_organized", "label": "clear_positive"},
        {"review_id": "1", "source": "frozen_organized", "label": "clear_positive"},
        {"review_id": "2", "source": "frozen_organized", "label": "clear_positive"},
        {"review_id": "3", "source": "frozen_organized", "label": "ambiguous"},
        {"review_id": "4", "source": "development_candidate", "label": "clear_positive"},
        {"review_id": "5", "source": "development_candidate", "label": "clear_positive"},
        {"review_id": "6", "source": "development_candidate", "label": "clear_positive"},
        {"review_id": "7", "source": "development_candidate", "label": "ambiguous"},
        {"review_id": "8", "source": "development_candidate", "label": "clear_negative"},
        {"review_id": "9", "source": "development_candidate", "label": "clear_negative"},
    ]

    summary = build_summary(candidates_payload, review_rows)

    assert summary["decision"] == "continue_optical_detector_research"
    assert summary["interpretation"] == "detector_problem"
