#!/usr/bin/env python3
"""Phase 2, Script 3: Calibrate scored segments against known Nova Scotia spots.

Loads scored segments and the 14 known surf spots, matches each known spot
to its nearest segment, and reports what score percentile each known spot
falls in. This validates whether the scoring heuristics rank known spots
above random coastline.

Output: pipeline/data/calibration_report.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SCORED_PATH = DATA_DIR / "coastline" / "ns_scored_segments.geojson"
KNOWN_SPOTS_PATH = DATA_DIR / "ns_known_spots.geojson"
OUTPUT_PATH = DATA_DIR / "calibration_report.json"

TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32620", always_xy=True)


def main() -> None:
    print("=" * 60)
    print("Phase 2, Step 3: Calibrate Against Known Spots")
    print("=" * 60)

    if not SCORED_PATH.exists():
        print(f"ERROR: {SCORED_PATH} not found. Run 11_score_geometry.py first.")
        sys.exit(1)

    if not KNOWN_SPOTS_PATH.exists():
        print(f"ERROR: {KNOWN_SPOTS_PATH} not found.")
        sys.exit(1)

    with SCORED_PATH.open() as f:
        scored = json.load(f)

    with KNOWN_SPOTS_PATH.open() as f:
        known = json.load(f)

    n_segments = len(scored["features"])
    n_known = len(known["features"])
    print(f"Loaded {n_segments} scored segments and {n_known} known spots")

    # Collect all scores for percentile calculation
    all_scores = sorted(
        [f["properties"]["total_score"] for f in scored["features"]]
    )

    # Build UTM geometries for segments (for distance matching)
    seg_geoms_utm = []
    for feat in scored["features"]:
        coords = feat["geometry"]["coordinates"]
        utm_coords = [TO_UTM.transform(x, y) for x, y in coords]
        seg_geoms_utm.append(LineString(utm_coords))

    # Match each known spot to nearest segment
    matches = []
    for spot_feat in known["features"]:
        spot_name = spot_feat["properties"]["name"]
        lon, lat = spot_feat["geometry"]["coordinates"]
        spot_utm = Point(TO_UTM.transform(lon, lat))

        # Find nearest segment
        best_idx = -1
        best_dist = float("inf")
        for j, seg_utm in enumerate(seg_geoms_utm):
            dist = seg_utm.distance(spot_utm)
            if dist < best_dist:
                best_dist = dist
                best_idx = j

        if best_idx < 0:
            matches.append({
                "spot_name": spot_name,
                "spot_lat": lat,
                "spot_lon": lon,
                "matched": False,
                "note": "No segment found",
            })
            continue

        matched_seg = scored["features"][best_idx]
        seg_props = matched_seg["properties"]
        seg_score = seg_props["total_score"]

        # Percentile: what fraction of segments score <= this segment
        rank_below = sum(1 for s in all_scores if s <= seg_score)
        percentile = round(100.0 * rank_below / n_segments, 1)

        matches.append({
            "spot_name": spot_name,
            "spot_region": spot_feat["properties"].get("region", ""),
            "spot_facing": spot_feat["properties"].get("facing", ""),
            "spot_lat": lat,
            "spot_lon": lon,
            "matched": True,
            "matched_segment_id": seg_props["segment_id"],
            "matched_segment_rank": seg_props["rank"],
            "distance_m": round(best_dist, 1),
            "segment_score": seg_score,
            "segment_orientation_deg": seg_props["orientation_deg"],
            "score_percentile": percentile,
            "score_breakdown": {
                "swell_exposure": seg_props["swell_exposure_score"],
                "geometry": seg_props["geometry_score"],
                "bathymetry": seg_props["bathymetry_score"],
                "road_access": seg_props["road_access_score"],
            },
        })

    # Summary statistics
    matched_spots = [m for m in matches if m.get("matched")]
    percentiles = [m["score_percentile"] for m in matched_spots]
    scores_matched = [m["segment_score"] for m in matched_spots]
    distances = [m["distance_m"] for m in matched_spots]

    summary = {
        "total_segments": n_segments,
        "total_known_spots": n_known,
        "matched_spots": len(matched_spots),
        "unmatched_spots": n_known - len(matched_spots),
        "score_stats": {
            "all_segments_mean": round(float(np.mean(all_scores)), 1),
            "all_segments_median": round(float(np.median(all_scores)), 1),
            "known_spots_mean_score": round(float(np.mean(scores_matched)), 1) if scores_matched else None,
            "known_spots_median_score": round(float(np.median(scores_matched)), 1) if scores_matched else None,
            "known_spots_mean_percentile": round(float(np.mean(percentiles)), 1) if percentiles else None,
            "known_spots_median_percentile": round(float(np.median(percentiles)), 1) if percentiles else None,
        },
        "distance_stats": {
            "mean_match_distance_m": round(float(np.mean(distances)), 1) if distances else None,
            "max_match_distance_m": round(float(np.max(distances)), 1) if distances else None,
        },
    }

    report = {
        "summary": summary,
        "spot_matches": matches,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print(f"\nWrote {OUTPUT_PATH}")

    # Print results
    print(f"\n{'='*60}")
    print("CALIBRATION RESULTS")
    print(f"{'='*60}")
    print(f"Total scored segments: {n_segments}")
    print(f"Known spots matched:   {len(matched_spots)}/{n_known}")

    if matched_spots:
        print(f"\nKnown spots mean score:       {summary['score_stats']['known_spots_mean_score']}")
        print(f"All segments mean score:      {summary['score_stats']['all_segments_mean']}")
        print(f"Known spots mean percentile:  {summary['score_stats']['known_spots_mean_percentile']}%")
        print(f"Known spots median percentile:{summary['score_stats']['known_spots_median_percentile']}%")

    print(f"\n{'Spot':<25} {'Score':>6} {'Pctile':>7} {'Rank':>6} {'Dist(m)':>8} {'Facing':>7}")
    print("-" * 65)
    for m in sorted(matched_spots, key=lambda x: x["score_percentile"], reverse=True):
        print(
            f"{m['spot_name']:<25} "
            f"{m['segment_score']:>6.1f} "
            f"{m['score_percentile']:>6.1f}% "
            f"{'#' + str(m['matched_segment_rank']):>6} "
            f"{m['distance_m']:>7.0f} "
            f"{m['spot_facing']:>7}"
        )

    # Unmatched spots
    unmatched = [m for m in matches if not m.get("matched")]
    if unmatched:
        print(f"\nUnmatched spots:")
        for m in unmatched:
            print(f"  {m['spot_name']}: {m.get('note', 'unknown reason')}")

    # Assessment
    if percentiles:
        median_pct = float(np.median(percentiles))
        print(f"\n{'='*60}")
        if median_pct >= 75:
            print("ASSESSMENT: Strong calibration — known spots rank in top quartile")
        elif median_pct >= 50:
            print("ASSESSMENT: Moderate calibration — known spots rank above median")
        elif median_pct >= 25:
            print("ASSESSMENT: Weak calibration — known spots near median, scoring needs tuning")
        else:
            print("ASSESSMENT: Poor calibration — known spots rank below median, review heuristics")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
