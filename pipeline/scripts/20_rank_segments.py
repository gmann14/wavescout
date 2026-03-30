#!/usr/bin/env python3
"""Phase 2.5, Script 20: Unified segment ranking.

Merges geometry scores, NIR foam evidence, and swell-response profiles into a
single composite score (0-100) per coastline segment.

Inputs:
  - pipeline/data/coastline/ns_scored_segments.geojson  (geometry scores)
  - pipeline/data/manifests/*_foam_detections.json       (all spots)
  - pipeline/data/manifests/*_swell_profiles.json        (all spots)

Outputs:
  - pipeline/data/coastline/ns_ranked_segments.geojson
  - pipeline/data/manifests/unified_ranking_manifest.json

Usage:
    python3 pipeline/scripts/20_rank_segments.py
    python3 pipeline/scripts/20_rank_segments.py --validate
    python3 pipeline/scripts/20_rank_segments.py --geometry-weight 0.35 --foam-weight 0.40 --profile-weight 0.25
    python3 pipeline/scripts/20_rank_segments.py --help
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from _script_utils import (
    generate_run_id,
    get_code_version,
    now_utc_iso,
    write_json,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
COASTLINE_DIR = DATA_DIR / "coastline"
MANIFESTS_DIR = DATA_DIR / "manifests"
SCORED_SEGMENTS_PATH = COASTLINE_DIR / "ns_scored_segments.geojson"
RANKED_SEGMENTS_PATH = COASTLINE_DIR / "ns_ranked_segments.geojson"
RANKING_MANIFEST_PATH = MANIFESTS_DIR / "unified_ranking_manifest.json"
CALIBRATION_PATH = DATA_DIR / "calibration_report.json"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_GEOMETRY_WEIGHT = 0.35
DEFAULT_FOAM_WEIGHT = 0.40
DEFAULT_PROFILE_WEIGHT = 0.25

# Foam scoring thresholds (matching spec)
QUALITY_SCORE_MIN = 60
FOAM_PRESENT_THRESHOLD = 0.05
FALSE_POSITIVE_FOAM_THRESHOLD = 0.2
FALSE_POSITIVE_SWELL_THRESHOLD = 0.5
FALSE_POSITIVE_PENALTY = 5.0


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_geometry_segments(path: Path) -> dict:
    """Load scored segments GeoJSON. Returns the full GeoJSON dict."""
    if not path.exists():
        print(f"ERROR: {path} not found. Run 11_score_geometry.py first.")
        sys.exit(1)

    with path.open() as f:
        data = json.load(f)

    print(f"Loaded {len(data['features'])} geometry-scored segments")
    return data


def load_all_foam_detections(manifests_dir: Path) -> dict[str, list[dict]]:
    """Load all foam detection manifests and group detections by segment_id.

    Returns:
        Dict mapping segment_id -> list of detection dicts.
    """
    by_segment: dict[str, list[dict]] = defaultdict(list)
    file_count = 0
    detection_count = 0

    for path in sorted(manifests_dir.glob("*_foam_detections.json")):
        try:
            with path.open() as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  WARN: Skipping {path.name}: {exc}")
            continue

        detections = data.get("detections", [])
        file_count += 1
        detection_count += len(detections)

        for det in detections:
            seg_id = det.get("segment_id")
            if seg_id:
                by_segment[seg_id].append(det)

    print(f"Loaded {detection_count} foam detections from {file_count} files")
    print(f"Segments with foam data: {len(by_segment)}")
    return dict(by_segment)


def load_all_swell_profiles(manifests_dir: Path) -> dict[str, dict]:
    """Load all swell profile manifests and index by segment_id.

    Returns:
        Dict mapping segment_id -> profile dict.
    """
    profiles: dict[str, dict] = {}
    file_count = 0

    for path in sorted(manifests_dir.glob("*_swell_profiles.json")):
        try:
            with path.open() as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  WARN: Skipping {path.name}: {exc}")
            continue

        file_count += 1
        for seg_id, profile in data.get("profiles", {}).items():
            if profile.get("status") == "complete":
                # Keep the profile with more observations if duplicate
                existing = profiles.get(seg_id)
                if existing is None or profile.get("observation_count", 0) > existing.get("observation_count", 0):
                    profiles[seg_id] = profile

    print(f"Loaded {len(profiles)} complete swell profiles from {file_count} files")
    return profiles


# ---------------------------------------------------------------------------
# Scoring components
# ---------------------------------------------------------------------------
def compute_foam_component(detections: list[dict]) -> tuple[float, dict]:
    """Compute foam evidence component (0-40) from detection observations.

    Returns:
        (score, metadata_dict)
    """
    # Filter to quality_score >= 60
    valid_obs = [
        d for d in detections
        if (d.get("quality_score") or 0) >= QUALITY_SCORE_MIN
        and d.get("foam_fraction") is not None
    ]

    if not valid_obs:
        return 0.0, {"foam_obs_count": 0, "status": "no_valid_observations"}

    fractions = [d["foam_fraction"] for d in valid_obs]
    max_foam_fraction = max(fractions)
    min_foam_fraction = min(fractions)

    # Mean foam fraction under swell >= 1.0m
    swell_obs = [
        d["foam_fraction"] for d in valid_obs
        if (d.get("swell_height_m") or 0) >= 1.0
    ]
    mean_foam_fraction_swell = float(np.mean(swell_obs)) if swell_obs else 0.0

    # Consistency: fraction of valid observations showing foam
    foam_present_count = sum(1 for f in fractions if f > FOAM_PRESENT_THRESHOLD)
    consistency = foam_present_count / len(valid_obs)

    # Dynamic range
    dynamic_range = max_foam_fraction - min_foam_fraction

    # Combine sub-scores (each 0-1, weighted)
    foam_raw = (
        0.35 * min(max_foam_fraction / 0.5, 1.0)
        + 0.30 * min(mean_foam_fraction_swell / 0.3, 1.0)
        + 0.20 * consistency
        + 0.15 * min(dynamic_range / 0.4, 1.0)
    )

    score = foam_raw * 40.0

    metadata = {
        "foam_obs_count": len(valid_obs),
        "max_foam_fraction": round(max_foam_fraction, 4),
        "mean_foam_fraction_swell": round(mean_foam_fraction_swell, 4),
        "consistency": round(consistency, 4),
        "dynamic_range": round(dynamic_range, 4),
    }

    return round(score, 2), metadata


def compute_profile_component(profile: dict) -> tuple[float, dict]:
    """Compute swell profile component (0-25) from a swell-response profile.

    Returns:
        (score, metadata_dict)
    """
    # Has turn-on threshold?
    has_turnon = 1.0 if profile.get("turn_on_threshold_m") is not None else 0.0

    # Has optimal range?
    optimal = profile.get("optimal_range") or {}
    has_optimal = 1.0 if optimal.get("min_m") is not None else 0.0

    # Direction specificity: proxy using responsive_directions
    # More concentrated = higher specificity
    responsive = profile.get("responsive_directions") or []
    dir_bins = profile.get("direction_bins") or {}
    total_dirs_with_data = len(dir_bins)

    if total_dirs_with_data > 0 and responsive:
        direction_concentration = 1.0 - (len(responsive) / 8.0)
        direction_concentration = max(0.0, min(1.0, direction_concentration))
    else:
        direction_concentration = 0.0

    # Observation depth
    obs_count = profile.get("observation_count", 0)
    obs_depth = min(obs_count / 30.0, 1.0)

    profile_raw = (
        0.25 * has_turnon
        + 0.25 * has_optimal
        + 0.25 * direction_concentration
        + 0.25 * obs_depth
    )

    score = profile_raw * 25.0

    metadata = {
        "turn_on_threshold": profile.get("turn_on_threshold_m"),
        "optimal_swell": (
            f"{optimal.get('min_m')}-{optimal.get('max_m')}m"
            if optimal.get("min_m") is not None
            else None
        ),
        "primary_direction": profile.get("primary_direction"),
        "observation_count": obs_count,
        "direction_concentration": round(direction_concentration, 4),
    }

    return round(score, 2), metadata


def compute_false_positive_penalty(detections: list[dict]) -> float:
    """Penalty for segments showing high foam on flat days (likely contamination).

    Returns penalty value (>= 0) to subtract from composite score.
    """
    valid_obs = [
        d for d in detections
        if (d.get("quality_score") or 0) >= QUALITY_SCORE_MIN
        and d.get("foam_fraction") is not None
        and d.get("swell_height_m") is not None
    ]

    flat_day_foam = [
        d for d in valid_obs
        if d["swell_height_m"] < FALSE_POSITIVE_SWELL_THRESHOLD
        and d["foam_fraction"] > FALSE_POSITIVE_FOAM_THRESHOLD
    ]

    if flat_day_foam:
        return FALSE_POSITIVE_PENALTY
    return 0.0


# ---------------------------------------------------------------------------
# Main composite scoring
# ---------------------------------------------------------------------------
def compute_composite_score(
    geometry_score: float,
    foam_detections: list[dict] | None,
    swell_profile: dict | None,
    geometry_weight: float,
    foam_weight: float,
    profile_weight: float,
) -> dict:
    """Compute composite score for a single segment.

    Returns dict with composite_score, confidence, components, and metadata.
    """
    components: dict[str, float] = {}
    metadata: dict[str, object] = {}
    available_weights: dict[str, float] = {}

    # Geometry component (always available for scored segments)
    geometry_component = (geometry_score / 100.0) * 35.0
    components["geometry_component"] = round(geometry_component, 2)
    available_weights["geometry"] = geometry_weight

    # Foam component
    foam_component = 0.0
    if foam_detections:
        foam_component, foam_meta = compute_foam_component(foam_detections)
        if foam_meta.get("foam_obs_count", 0) > 0:
            components["foam_component"] = foam_component
            available_weights["foam"] = foam_weight
            metadata.update(foam_meta)
        else:
            components["foam_component"] = 0.0

    if "foam_component" not in components:
        components["foam_component"] = 0.0

    # Profile component
    profile_component = 0.0
    if swell_profile:
        profile_component, profile_meta = compute_profile_component(swell_profile)
        components["profile_component"] = profile_component
        available_weights["profile"] = profile_weight
        metadata.update(profile_meta)
    else:
        components["profile_component"] = 0.0

    # Confidence = count of available components
    confidence = len(available_weights)

    # Redistribute weights proportionally among available components
    total_available_weight = sum(available_weights.values())
    if total_available_weight <= 0:
        return {
            "composite_score": 0.0,
            "confidence": 0,
            **components,
            **metadata,
        }

    # Scale factor: 1.0 / total_available_weight normalizes so components fill 0-100
    scale = 1.0 / total_available_weight

    # Compute weighted composite
    composite = 0.0
    if "geometry" in available_weights:
        composite += geometry_component * available_weights["geometry"] * scale
    if "foam" in available_weights:
        composite += foam_component * available_weights["foam"] * scale
    if "profile" in available_weights:
        composite += profile_component * available_weights["profile"] * scale

    # Scale to 0-100 range
    # The max possible raw composite is:
    #   35 * (w_g * scale) + 40 * (w_f * scale) + 25 * (w_p * scale)
    # With all 3 components: 35*0.35/1.0 + 40*0.40/1.0 + 25*0.25/1.0 = 12.25 + 16 + 6.25 = 34.5
    # We need to normalize to 0-100
    max_possible = 0.0
    if "geometry" in available_weights:
        max_possible += 35.0 * available_weights["geometry"] * scale
    if "foam" in available_weights:
        max_possible += 40.0 * available_weights["foam"] * scale
    if "profile" in available_weights:
        max_possible += 25.0 * available_weights["profile"] * scale

    if max_possible > 0:
        composite_normalized = (composite / max_possible) * 100.0
    else:
        composite_normalized = 0.0

    # Apply false positive penalty
    penalty = 0.0
    if foam_detections:
        penalty = compute_false_positive_penalty(foam_detections)
        if penalty > 0:
            composite_normalized = max(0.0, composite_normalized - penalty)
            metadata["false_positive_penalty"] = penalty

    return {
        "composite_score": round(composite_normalized, 1),
        "confidence": confidence,
        **components,
        **metadata,
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_known_spots(
    segments_by_id: dict[str, dict],
    calibration_path: Path,
) -> bool:
    """Check that known spots still rank in a reasonable percentile range.

    Returns True if validation passes.
    """
    if not calibration_path.exists():
        print("\nWARN: calibration_report.json not found, skipping validation")
        return True

    with calibration_path.open() as f:
        cal = json.load(f)

    spot_matches = cal.get("spot_matches", [])
    if not spot_matches:
        print("\nWARN: No spot matches in calibration report")
        return True

    # Collect all composite scores for percentile calculation
    all_scores = sorted(
        [seg.get("composite_score", 0) for seg in segments_by_id.values()],
        reverse=True,
    )
    n = len(all_scores)

    print(f"\n{'=' * 60}")
    print("VALIDATION: Known spots vs composite ranking")
    print(f"{'=' * 60}")
    print(f"{'Spot':<30} {'Seg ID':<16} {'Composite':>10} {'Percentile':>11}")
    print("-" * 70)

    issues = []
    for match in spot_matches:
        seg_id = match.get("matched_segment_id")
        spot_name = match.get("spot_name", "?")
        if not seg_id or seg_id not in segments_by_id:
            print(f"  {spot_name:<30} {'(not found)':<16}")
            continue

        seg = segments_by_id[seg_id]
        comp_score = seg.get("composite_score", 0)

        # Calculate percentile
        rank = sum(1 for s in all_scores if s > comp_score) + 1
        percentile = round((1.0 - rank / n) * 100, 1)

        status = ""
        if percentile < 50:
            status = " <-- LOW"
            issues.append(f"{spot_name}: {percentile}th percentile")

        print(f"  {spot_name:<30} {seg_id:<16} {comp_score:>10.1f} {percentile:>10.1f}%{status}")

    if issues:
        print(f"\nWARN: {len(issues)} known spots ranked below 50th percentile:")
        for issue in issues:
            print(f"  - {issue}")
        return False

    print("\nValidation PASSED: all known spots rank above 50th percentile")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Unified segment ranking: merge geometry scores, NIR foam evidence, "
            "and swell-response profiles into a single composite score per segment."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 pipeline/scripts/20_rank_segments.py
  python3 pipeline/scripts/20_rank_segments.py --validate
  python3 pipeline/scripts/20_rank_segments.py --geometry-weight 0.40 --foam-weight 0.35

Output files:
  pipeline/data/coastline/ns_ranked_segments.geojson
  pipeline/data/manifests/unified_ranking_manifest.json
""",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Check that known spots still rank well (uses calibration_report.json).",
    )
    parser.add_argument(
        "--geometry-weight",
        type=float,
        default=DEFAULT_GEOMETRY_WEIGHT,
        help=f"Weight for geometry component. Default: {DEFAULT_GEOMETRY_WEIGHT}",
    )
    parser.add_argument(
        "--foam-weight",
        type=float,
        default=DEFAULT_FOAM_WEIGHT,
        help=f"Weight for foam evidence component. Default: {DEFAULT_FOAM_WEIGHT}",
    )
    parser.add_argument(
        "--profile-weight",
        type=float,
        default=DEFAULT_PROFILE_WEIGHT,
        help=f"Weight for swell profile component. Default: {DEFAULT_PROFILE_WEIGHT}",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("Phase 2.5, Step 20: Unified Segment Ranking")
    print("=" * 60)

    # Validate weights sum to ~1.0
    total_weight = args.geometry_weight + args.foam_weight + args.profile_weight
    if abs(total_weight - 1.0) > 0.01:
        print(f"ERROR: Weights must sum to 1.0 (got {total_weight:.3f})")
        sys.exit(1)

    print(f"Weights: geometry={args.geometry_weight}, foam={args.foam_weight}, profile={args.profile_weight}")

    # 1. Load geometry scores
    print("\n--- Loading geometry scores ---")
    geo_data = load_geometry_segments(SCORED_SEGMENTS_PATH)

    # 2. Load foam detections (grouped by segment_id)
    print("\n--- Loading foam detections ---")
    foam_by_segment = load_all_foam_detections(MANIFESTS_DIR)

    # 3. Load swell profiles (indexed by segment_id)
    print("\n--- Loading swell profiles ---")
    profiles_by_segment = load_all_swell_profiles(MANIFESTS_DIR)

    # 4. Compute composite score per segment
    print(f"\n--- Computing composite scores ---")
    scored_props: dict[str, dict] = {}
    skipped = 0

    for feat in geo_data["features"]:
        props = feat["properties"]
        seg_id = props["segment_id"]
        geometry_score = props.get("total_score", 0)

        # Skip segments with geometry_score == 0 (unexposed)
        if geometry_score <= 0:
            skipped += 1
            continue

        foam_dets = foam_by_segment.get(seg_id)
        profile = profiles_by_segment.get(seg_id)

        result = compute_composite_score(
            geometry_score=geometry_score,
            foam_detections=foam_dets,
            swell_profile=profile,
            geometry_weight=args.geometry_weight,
            foam_weight=args.foam_weight,
            profile_weight=args.profile_weight,
        )

        # Merge result into properties
        props["composite_score"] = result["composite_score"]
        props["confidence"] = result["confidence"]
        props["geometry_component"] = result["geometry_component"]
        props["foam_component"] = result["foam_component"]
        props["profile_component"] = result["profile_component"]

        # Add useful metadata if available
        if result.get("foam_obs_count"):
            props["foam_obs_count"] = result["foam_obs_count"]
        if result.get("turn_on_threshold") is not None:
            props["turn_on_threshold"] = result["turn_on_threshold"]
        if result.get("optimal_swell") is not None:
            props["optimal_swell"] = result["optimal_swell"]
        if result.get("primary_direction") is not None:
            props["primary_direction"] = result["primary_direction"]
        if result.get("false_positive_penalty"):
            props["false_positive_penalty"] = result["false_positive_penalty"]

        scored_props[seg_id] = props

    print(f"Scored: {len(scored_props)} segments (skipped {skipped} with score=0)")

    # 5. Rank and assign percentiles
    # Sort features by composite_score descending
    valid_features = [
        f for f in geo_data["features"]
        if f["properties"].get("composite_score") is not None
    ]
    valid_features.sort(
        key=lambda f: f["properties"]["composite_score"],
        reverse=True,
    )

    n = len(valid_features)
    for i, feat in enumerate(valid_features):
        feat["properties"]["rank"] = i + 1
        feat["properties"]["percentile"] = round((1.0 - (i + 1) / n) * 100, 1)

    # Replace features in geo_data (keep only scored ones)
    geo_data["features"] = valid_features

    # 6. Write output
    print(f"\n--- Writing output ---")
    RANKED_SEGMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RANKED_SEGMENTS_PATH.open("w") as f:
        json.dump(geo_data, f)
    print(f"Wrote {RANKED_SEGMENTS_PATH} ({RANKED_SEGMENTS_PATH.stat().st_size / (1024 * 1024):.1f}MB)")

    # Build summary manifest
    all_scores = [f["properties"]["composite_score"] for f in valid_features]
    scores_array = np.array(all_scores)

    segments_with_foam = sum(
        1 for f in valid_features
        if f["properties"].get("foam_obs_count", 0) > 0
    )
    segments_with_profiles = sum(
        1 for f in valid_features
        if f["properties"].get("confidence", 0) >= 3
    )
    confidence_dist = {
        "confidence_1": sum(1 for f in valid_features if f["properties"].get("confidence") == 1),
        "confidence_2": sum(1 for f in valid_features if f["properties"].get("confidence") == 2),
        "confidence_3": sum(1 for f in valid_features if f["properties"].get("confidence") == 3),
    }

    top_50 = [f["properties"]["segment_id"] for f in valid_features[:50]]

    run_id = generate_run_id()
    manifest = {
        "script": "20_rank_segments.py",
        "run_id": run_id,
        "generated_at_utc": now_utc_iso(),
        "code_version": get_code_version(),
        "parameters": {
            "geometry_weight": args.geometry_weight,
            "foam_weight": args.foam_weight,
            "profile_weight": args.profile_weight,
            "quality_score_min": QUALITY_SCORE_MIN,
            "false_positive_foam_threshold": FALSE_POSITIVE_FOAM_THRESHOLD,
            "false_positive_swell_threshold": FALSE_POSITIVE_SWELL_THRESHOLD,
            "false_positive_penalty": FALSE_POSITIVE_PENALTY,
        },
        "total_segments": n,
        "segments_with_foam": segments_with_foam,
        "segments_with_profiles": segments_with_profiles,
        "confidence_distribution": confidence_dist,
        "score_distribution": {
            "min": round(float(np.min(scores_array)), 1),
            "max": round(float(np.max(scores_array)), 1),
            "mean": round(float(np.mean(scores_array)), 1),
            "median": round(float(np.median(scores_array)), 1),
            "p50": round(float(np.percentile(scores_array, 50)), 1),
            "p75": round(float(np.percentile(scores_array, 75)), 1),
            "p90": round(float(np.percentile(scores_array, 90)), 1),
            "p95": round(float(np.percentile(scores_array, 95)), 1),
            "p99": round(float(np.percentile(scores_array, 99)), 1),
        },
        "top_50": top_50,
    }

    write_json(RANKING_MANIFEST_PATH, manifest)
    print(f"Wrote {RANKING_MANIFEST_PATH}")

    # Print summary
    print(f"\n{'=' * 60}")
    print("RESULTS")
    print(f"{'=' * 60}")
    print(f"Total ranked segments: {n}")
    print(f"Segments with foam data: {segments_with_foam}")
    print(f"Segments with full profile: {segments_with_profiles}")
    print(f"Confidence distribution: {confidence_dist}")
    print(f"\nScore distribution:")
    print(f"  Min:    {manifest['score_distribution']['min']}")
    print(f"  Median: {manifest['score_distribution']['median']}")
    print(f"  Mean:   {manifest['score_distribution']['mean']}")
    print(f"  P90:    {manifest['score_distribution']['p90']}")
    print(f"  P95:    {manifest['score_distribution']['p95']}")
    print(f"  P99:    {manifest['score_distribution']['p99']}")
    print(f"  Max:    {manifest['score_distribution']['max']}")

    # Top 10
    print(f"\nTop 10 segments:")
    for feat in valid_features[:10]:
        p = feat["properties"]
        conf_label = {1: "geom", 2: "geom+foam", 3: "full"}.get(p.get("confidence", 1), "?")
        print(
            f"  #{p['rank']} {p['segment_id']}: "
            f"composite={p['composite_score']}, "
            f"confidence={conf_label}, "
            f"geo={p.get('geometry_component', 0):.1f}, "
            f"foam={p.get('foam_component', 0):.1f}, "
            f"profile={p.get('profile_component', 0):.1f}"
        )

    # 7. Validation (optional)
    if args.validate:
        segments_by_id = {
            f["properties"]["segment_id"]: f["properties"]
            for f in valid_features
        }
        passed = validate_known_spots(segments_by_id, CALIBRATION_PATH)
        if not passed:
            print("\nValidation WARNING — some known spots rank low (may be calibration artifacts)")
            print("Key spots (Lawrencetown, Martinique, Cow Bay, etc.) should rank above 85th percentile")


if __name__ == "__main__":
    main()
