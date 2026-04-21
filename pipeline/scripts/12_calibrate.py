#!/usr/bin/env python3
"""Build a current spot-neighborhood calibration report from ranked segments.

This replaces the old nearest-segment calibration output with a spot-centered
view of the nearby ranked field around trusted named spots.

Output: pipeline/data/calibration_report.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _ranking_support import (
    DEFAULT_WATCHLIST_WITHIN_DISTANCE_M,
    build_spot_neighborhood_report,
    classify_watchlist_action,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RANKED_PATH = DATA_DIR / "coastline" / "ns_ranked_segments.geojson"
SPOTS_PATH = DATA_DIR / "ns_spots.geojson"
UNIFIED_SPOTS_PATH = DATA_DIR / "unified_spots.json"
SPOT_NEIGHBORHOOD_REGRESSIONS_PATH = DATA_DIR / "spot_neighborhood_regressions.json"
OUTPUT_PATH = DATA_DIR / "calibration_report.json"


def main() -> None:
    print("=" * 60)
    print("Phase 2.5, Step 12: Build Spot-Neighborhood Calibration Report")
    print("=" * 60)

    if not RANKED_PATH.exists():
        print(f"ERROR: {RANKED_PATH} not found. Run 20_rank_segments.py first.")
        sys.exit(1)
    if not SPOTS_PATH.exists():
        print(f"ERROR: {SPOTS_PATH} not found.")
        sys.exit(1)

    ranked = json.loads(RANKED_PATH.read_text())
    spots = json.loads(SPOTS_PATH.read_text())
    regressions = (
        json.loads(SPOT_NEIGHBORHOOD_REGRESSIONS_PATH.read_text())
        if SPOT_NEIGHBORHOOD_REGRESSIONS_PATH.exists()
        else None
    )

    report = build_spot_neighborhood_report(
        ranked.get("features", []),
        spots,
        regressions,
    )
    watchlist_report = None
    if UNIFIED_SPOTS_PATH.exists():
        unified_spots = json.loads(UNIFIED_SPOTS_PATH.read_text())
        watchlist_report = build_spot_neighborhood_report(
            ranked.get("features", []),
            unified_spots,
            None,
            default_within_distance_m=DEFAULT_WATCHLIST_WITHIN_DISTANCE_M,
        )
        watchlist_items = watchlist_report.get("spot_neighborhoods", [])
        tracked_slugs = {item.get("slug") for item in report.get("spot_neighborhoods", [])}
        for item in watchlist_items:
            action, reason = classify_watchlist_action(item, tracked_slugs=tracked_slugs)
            item["watchlist_action"] = action
            item["watchlist_reason"] = reason
            item["watchlist_has_config"] = item.get("config_point_lon") is not None

        candidate_items = [
            item for item in watchlist_items
            if item.get("watchlist_action") in {"priority_regression_candidate", "research_candidate"}
        ]
        candidate_items.sort(key=lambda item: float(item.get("best_segment_score", 0.0)), reverse=True)
        watchlist_report["summary"]["score_bands"] = {
            "ge_70": sum(1 for item in watchlist_items if float(item.get("best_segment_score", 0.0)) >= 70.0),
            "ge_60": sum(
                1 for item in watchlist_items
                if 60.0 <= float(item.get("best_segment_score", 0.0)) < 70.0
            ),
            "ge_50": sum(
                1 for item in watchlist_items
                if 50.0 <= float(item.get("best_segment_score", 0.0)) < 60.0
            ),
            "lt_50": sum(1 for item in watchlist_items if float(item.get("best_segment_score", 0.0)) < 50.0),
        }
        watchlist_report["summary"]["watchlist_action_counts"] = {
            "already_tracked": sum(1 for item in watchlist_items if item.get("watchlist_action") == "already_tracked"),
            "priority_regression_candidate": sum(
                1 for item in watchlist_items
                if item.get("watchlist_action") == "priority_regression_candidate"
            ),
            "research_candidate": sum(
                1 for item in watchlist_items if item.get("watchlist_action") == "research_candidate"
            ),
            "coordinate_review_candidate": sum(
                1 for item in watchlist_items if item.get("watchlist_action") == "coordinate_review_candidate"
            ),
            "secondary_watch": sum(
                1 for item in watchlist_items if item.get("watchlist_action") == "secondary_watch"
            ),
            "low_signal_watch": sum(
                1 for item in watchlist_items if item.get("watchlist_action") == "low_signal_watch"
            ),
            "no_segment_support": sum(
                1 for item in watchlist_items if item.get("watchlist_action") == "no_segment_support"
            ),
        }
        watchlist_report["summary"]["top_watchlist_candidates"] = [
            {
                "slug": item.get("slug"),
                "score": round(float(item.get("best_segment_score", 0.0)), 1),
                "source": item.get("spot_source"),
                "action": item.get("watchlist_action"),
                "reason": item.get("watchlist_reason"),
            }
            for item in candidate_items[:12]
        ]
        report["public_watchlist"] = watchlist_report

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    print(f"Wrote {OUTPUT_PATH}")

    summary = report.get("summary", {})
    print(f"\nTrusted spots: {summary.get('trusted_spot_count', 0)}")
    print(f"Tracked spots: {summary.get('tracked_spot_count', 0)}")
    print(
        "Tracked spots meeting expectations: "
        f"{summary.get('spots_meeting_expectations', 0)}/"
        f"{summary.get('tracked_spot_count', 0)}"
    )
    follow_up_counts = summary.get("follow_up_counts", {})
    print(
        "Follow-ups: "
        f"coordinate/source={follow_up_counts.get('coordinate_or_source_review', 0)}, "
        f"spot-definition={follow_up_counts.get('spot_definition_review', 0)}, "
        f"ranking={follow_up_counts.get('ranking_review', 0)}, "
        f"untracked={follow_up_counts.get('untracked', 0)}"
    )
    if watchlist_report is not None:
        watchlist_summary = watchlist_report.get("summary", {})
        score_bands = watchlist_summary.get("score_bands", {})
        print(
            "Public watchlist: "
            f"{watchlist_summary.get('trusted_spot_count', 0)} spots, "
            f">=70={score_bands.get('ge_70', 0)}, "
            f"60-69={score_bands.get('ge_60', 0)}, "
            f"50-59={score_bands.get('ge_50', 0)}, "
            f"<50={score_bands.get('lt_50', 0)}"
        )
        action_counts = watchlist_summary.get("watchlist_action_counts", {})
        print(
            "Watchlist actions: "
            f"priority={action_counts.get('priority_regression_candidate', 0)}, "
            f"research={action_counts.get('research_candidate', 0)}, "
            f"coord-review={action_counts.get('coordinate_review_candidate', 0)}, "
            f"secondary={action_counts.get('secondary_watch', 0)}, "
            f"low-signal={action_counts.get('low_signal_watch', 0)}, "
            f"no-support={action_counts.get('no_segment_support', 0)}"
        )

    print(
        f"\n{'Spot':<24} {'Best':>6} {'Local':>6} {'>=50':>5} {'>=60':>5} {'>=70':>5} {'Status':>10}"
    )
    print("-" * 71)
    for item in report.get("spot_neighborhoods", []):
        if not item.get("tracked_by_regression"):
            status = "untracked"
        else:
            status = "pass" if item.get("meets_expectations") else "fail"
        local_score = item.get("best_score_within_distance")
        local_display = f"{float(local_score):.1f}" if local_score is not None else "-"
        print(
            f"{item.get('spot_name', item.get('slug', '?')):<24} "
            f"{float(item.get('best_segment_score', 0.0)):>6.1f} "
            f"{local_display:>6} "
            f"{int(item.get('count_ge_50', 0)):>5} "
            f"{int(item.get('count_ge_60', 0)):>5} "
            f"{int(item.get('count_ge_70', 0)):>5} "
            f"{status:>10}"
        )

    failing = [
        item
        for item in report.get("spot_neighborhoods", [])
        if item.get("tracked_by_regression") and not item.get("meets_expectations")
    ]
    if failing:
        print("\nFailing spots:")
        for item in failing:
            print(f"  {item.get('slug')}:")
            confidence = item.get("best_segment_confidence")
            sparsity_penalty = item.get("best_segment_evidence_sparsity_penalty")
            false_positive_penalty = item.get("best_segment_false_positive_penalty")
            if confidence is not None:
                print(
                    "    "
                    f"best-segment confidence={confidence}, "
                    f"evidence-penalty={float(sparsity_penalty or 0.0):.1f}, "
                    f"false-positive-penalty={float(false_positive_penalty or 0.0):.1f}"
                )
            for issue in item.get("issues", []):
                print(f"    - {issue}")

    follow_ups = [item for item in report.get("follow_up_items", []) if item.get("action") != "untracked"]
    if follow_ups:
        print("\nRecommended follow-ups:")
        for item in follow_ups:
            print(f"  {item.get('slug')}: {item.get('action')} — {item.get('reason')}")

    if watchlist_report is not None:
        weak_watchlist = sorted(
            watchlist_report.get("spot_neighborhoods", []),
            key=lambda item: float(item.get("best_segment_score", 0.0)),
        )[:8]
        candidate_watchlist = watchlist_report.get("summary", {}).get("top_watchlist_candidates", [])
        print("\nTop watchlist expansion candidates:")
        for item in candidate_watchlist:
            print(
                f"  {item.get('slug')}: "
                f"best={float(item.get('score', 0.0)):.1f}, "
                f"source={item.get('source')}, "
                f"action={item.get('action')}"
            )
        coordinate_review_watchlist = [
            item for item in watchlist_report.get("spot_neighborhoods", [])
            if item.get("watchlist_action") == "coordinate_review_candidate"
        ]
        if coordinate_review_watchlist:
            print("\nWatchlist coordinate-review candidates:")
            for item in sorted(
                coordinate_review_watchlist,
                key=lambda item: float(item.get("best_segment_score", 0.0)),
                reverse=True,
            )[:8]:
                distance = item.get("best_segment_distance_m")
                distance_display = f"{float(distance):.1f}m" if distance is not None else "n/a"
                print(
                    f"  {item.get('slug')}: "
                    f"best={float(item.get('best_segment_score', 0.0)):.1f}, "
                    f"distance={distance_display}, "
                    f"source={item.get('spot_source')}"
                )
        print("\nPublic watchlist weakest spots:")
        for item in weak_watchlist:
            print(
                f"  {item.get('slug')}: "
                f"best={float(item.get('best_segment_score', 0.0)):.1f}, "
                f"source={item.get('spot_source')}"
            )


if __name__ == "__main__":
    main()
