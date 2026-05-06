#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.research.swell_lines import CALIBRATION_PAIRS_PATH  # noqa: E402
from pipeline.research.swell_lines_v5 import (  # noqa: E402
    CANDIDATE_SCENES_PATH,
    REPORT_PATH,
    REVIEW_IMAGES_DIR,
    SCENE_CATALOG_PATH,
    SCENE_REVIEWS_PATH,
    SUMMARY_PATH,
)
from pipeline.research.swell_lines_v5.signal_validation import (  # noqa: E402
    DEFAULT_FOAM_MANIFESTS_DIR,
    DEFAULT_GALLERY_MANIFEST_PATH,
    DEFAULT_GEE_PROJECT,
    build_candidate_scenes,
    build_scene_catalog,
    build_summary,
    ensure_candidate_review_images,
    selection_defaults,
    write_json,
    write_review_template,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze the v5 signal-validation review set.")
    parser.add_argument("--pairs", type=Path, default=CALIBRATION_PAIRS_PATH)
    parser.add_argument("--manifests-dir", type=Path, default=DEFAULT_FOAM_MANIFESTS_DIR)
    parser.add_argument("--gallery-manifest", type=Path, default=DEFAULT_GALLERY_MANIFEST_PATH)
    parser.add_argument("--scene-catalog", type=Path, default=SCENE_CATALOG_PATH)
    parser.add_argument("--output", type=Path, default=CANDIDATE_SCENES_PATH)
    parser.add_argument("--reviews", type=Path, default=SCENE_REVIEWS_PATH)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--review-images-dir", type=Path, default=REVIEW_IMAGES_DIR)
    parser.add_argument("--profile", choices=("strict", "broad"), default="broad")
    parser.add_argument("--max-additional-per-spot", type=int)
    parser.add_argument("--max-cloud-pct", type=float)
    parser.add_argument("--min-quality-score", type=float)
    parser.add_argument("--min-swell-height-m", type=float)
    parser.add_argument("--min-swell-period-s", type=float)
    parser.add_argument("--refresh-gee", action="store_true", help="Query GEE for clear scenes after the latest local manifest date.")
    parser.add_argument("--refresh-end-date", help="Last date to include when refreshing GEE scene metadata. Defaults to today.")
    parser.add_argument("--project", default=DEFAULT_GEE_PROJECT, help=f"GEE project ID. Default: {DEFAULT_GEE_PROJECT}")
    parser.add_argument("--export-images", action="store_true", help="Export RGB/NIR review images for candidates with missing local paths.")
    parser.add_argument("--force-image-export", action="store_true", help="Re-export review images even if local files already exist.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    defaults = selection_defaults(args.profile)
    scene_catalog = build_scene_catalog(
        pairs_path=args.pairs,
        manifests_dir=args.manifests_dir,
        gallery_manifest_path=args.gallery_manifest,
        refresh_recent=args.refresh_gee,
        gee_project=args.project,
        refresh_end_date=args.refresh_end_date,
    )
    write_json(args.scene_catalog, scene_catalog)

    candidates_payload = build_candidate_scenes(
        scene_catalog=scene_catalog,
        pairs_path=args.pairs,
        profile=args.profile,
        max_additional_per_spot=args.max_additional_per_spot,
        max_cloud_pct=args.max_cloud_pct,
        min_quality_score=args.min_quality_score,
        min_swell_height_m=args.min_swell_height_m,
        min_swell_period_s=args.min_swell_period_s,
    )
    if args.export_images:
        candidates_payload = ensure_candidate_review_images(
            candidates_payload,
            review_images_dir=args.review_images_dir,
            gee_project=args.project,
            force=args.force_image_export,
        )

    write_json(args.output, candidates_payload)
    review_rows = write_review_template(candidates_payload, reviews_path=args.reviews)
    summary = build_summary(candidates_payload, review_rows)
    write_json(args.summary, summary)
    print(
        json.dumps(
            {
                "profile": args.profile,
                "criteria": {
                    "max_cloud_pct": candidates_payload["criteria"]["max_cloud_pct"],
                    "min_quality_score": candidates_payload["criteria"]["min_quality_score"],
                    "min_swell_height_m": candidates_payload["criteria"]["min_swell_height_m"],
                    "min_swell_period_s": candidates_payload["criteria"]["min_swell_period_s"],
                    "max_additional_per_spot": candidates_payload["criteria"]["max_additional_per_spot"],
                },
                "catalog_scene_count": scene_catalog["summary"]["scene_count"],
                "catalog_refreshed_scene_count": scene_catalog["summary"]["refreshed_scene_count"],
                "candidate_scene_count": candidates_payload["summary"]["selected_scene_count"],
                "shortfall": candidates_payload["summary"]["shortfall"],
                "pending_scene_count": summary["pending_scene_count"],
                "decision": summary["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
