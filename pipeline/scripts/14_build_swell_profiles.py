#!/usr/bin/env python3
"""Phase 2.5, Script 14: Build swell-response profiles per coastline segment.

Reads foam detection output from 13_detect_foam_nir.py and builds a
swell-response profile for each segment:

  - turn_on_threshold: minimum swell height where foam_fraction > 0.05
  - optimal_range: swell height range where foam_fraction is highest
  - blow_out_point: swell height where foam becomes uniform (foam_fraction > 0.8)
  - primary_direction: swell directions that produce the most foam
  - observation_count: number of valid observations per segment

Output: pipeline/data/manifests/<slug>_swell_profiles.json

Usage:
    python3 pipeline/scripts/14_build_swell_profiles.py
    python3 pipeline/scripts/14_build_swell_profiles.py --input pipeline/data/manifests/lawrencetown-beach_foam_detections.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from _script_utils import (
    DEFAULT_CONFIG_PATH,
    default_manifest_path,
    generate_run_id,
    get_code_version,
    load_region_config,
    now_utc_iso,
    write_json,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Foam fraction thresholds for profile classification
FOAM_PRESENT_THRESHOLD = 0.05     # foam_fraction above this = "foam present"
FOAM_BLOWOUT_THRESHOLD = 0.80    # foam_fraction above this = "blown out"
FOAM_OPTIMAL_THRESHOLD = 0.15    # foam_fraction above this = "good breaking"

# Minimum observations needed to build a profile
MIN_OBSERVATIONS = 3

# Swell height bins for profile analysis (meters)
SWELL_BIN_EDGES = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0]

# Direction bins (degrees, 8 compass sectors)
DIR_BIN_EDGES = [0, 45, 90, 135, 180, 225, 270, 315, 360]
DIR_BIN_LABELS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


# ---------------------------------------------------------------------------
# Profile builders
# ---------------------------------------------------------------------------
def bin_swell_height(height: float) -> str:
    """Assign a swell height to a named bin."""
    for i in range(len(SWELL_BIN_EDGES) - 1):
        if SWELL_BIN_EDGES[i] <= height < SWELL_BIN_EDGES[i + 1]:
            return f"{SWELL_BIN_EDGES[i]:.1f}-{SWELL_BIN_EDGES[i + 1]:.1f}m"
    return f">{SWELL_BIN_EDGES[-1]:.1f}m"


def bin_direction(deg: float) -> str:
    """Assign a swell direction to a compass sector."""
    deg = deg % 360
    for i in range(len(DIR_BIN_EDGES) - 1):
        if DIR_BIN_EDGES[i] <= deg < DIR_BIN_EDGES[i + 1]:
            return DIR_BIN_LABELS[i]
    return DIR_BIN_LABELS[0]  # 360 wraps to N


def build_profile(observations: list[dict]) -> dict:
    """Build a swell-response profile for a single segment.

    Args:
        observations: List of detection dicts for this segment, each with
            swell_height_m, swell_direction_deg, foam_fraction, etc.

    Returns:
        Profile dict with thresholds, optimal range, and direction analysis.
    """
    # Filter to observations with valid swell data
    valid = [
        obs for obs in observations
        if obs.get("swell_height_m") is not None
        and obs.get("foam_fraction") is not None
    ]

    if len(valid) < MIN_OBSERVATIONS:
        return {
            "status": "insufficient_data",
            "observation_count": len(valid),
            "min_observations_required": MIN_OBSERVATIONS,
        }

    # Sort by swell height for threshold analysis
    by_swell = sorted(valid, key=lambda o: o["swell_height_m"])

    heights = np.array([o["swell_height_m"] for o in by_swell])
    fractions = np.array([o["foam_fraction"] for o in by_swell])

    # --- Turn-on threshold ---
    turn_on = None
    for obs in by_swell:
        if obs["foam_fraction"] > FOAM_PRESENT_THRESHOLD:
            turn_on = obs["swell_height_m"]
            break

    # --- Blow-out point ---
    blow_out = None
    for obs in by_swell:
        if obs["foam_fraction"] > FOAM_BLOWOUT_THRESHOLD:
            blow_out = obs["swell_height_m"]
            break

    # --- Optimal range (swell heights producing the best foam) ---
    # Group by swell height bins and find the bin with the highest mean foam_fraction
    bin_data: dict[str, list[float]] = defaultdict(list)
    for obs in valid:
        b = bin_swell_height(obs["swell_height_m"])
        bin_data[b].append(obs["foam_fraction"])

    bin_means = {}
    for b, fracs in bin_data.items():
        bin_means[b] = {
            "mean_foam_fraction": round(float(np.mean(fracs)), 4),
            "observation_count": len(fracs),
        }

    # Find the optimal bin (highest mean foam_fraction with at least 2 observations)
    best_bin = None
    best_mean = 0.0
    for b, info in bin_means.items():
        if info["observation_count"] >= 2 and info["mean_foam_fraction"] > best_mean:
            best_mean = info["mean_foam_fraction"]
            best_bin = b

    # Optimal range: all bins where mean foam_fraction > FOAM_OPTIMAL_THRESHOLD
    optimal_bins = [
        b for b, info in bin_means.items()
        if info["mean_foam_fraction"] > FOAM_OPTIMAL_THRESHOLD
        and info["observation_count"] >= 2
    ]

    # Parse optimal range into min/max swell heights
    optimal_min = None
    optimal_max = None
    if optimal_bins:
        heights_in_optimal = []
        for b in optimal_bins:
            parts = b.replace("m", "").split("-")
            if len(parts) == 2:
                heights_in_optimal.extend([float(parts[0]), float(parts[1])])
            elif b.startswith(">"):
                heights_in_optimal.append(float(b[1:].replace("m", "")))
        if heights_in_optimal:
            optimal_min = min(heights_in_optimal)
            optimal_max = max(heights_in_optimal)

    # --- Primary direction ---
    dir_data: dict[str, list[float]] = defaultdict(list)
    for obs in valid:
        d = obs.get("swell_direction_deg")
        if d is not None:
            sector = bin_direction(d)
            dir_data[sector].append(obs["foam_fraction"])

    dir_means = {}
    best_dir = None
    best_dir_mean = 0.0
    for sector, fracs in dir_data.items():
        mean_f = float(np.mean(fracs))
        dir_means[sector] = {
            "mean_foam_fraction": round(mean_f, 4),
            "observation_count": len(fracs),
        }
        if len(fracs) >= 2 and mean_f > best_dir_mean:
            best_dir_mean = mean_f
            best_dir = sector

    # Responsive directions: sectors where mean foam > threshold
    responsive_dirs = [
        s for s, info in dir_means.items()
        if info["mean_foam_fraction"] > FOAM_PRESENT_THRESHOLD
        and info["observation_count"] >= 2
    ]

    # --- Overall stats ---
    all_fracs = [o["foam_fraction"] for o in valid]
    all_nirs = [o["mean_nir"] for o in valid if o.get("mean_nir") is not None]

    return {
        "status": "complete",
        "observation_count": len(valid),
        "turn_on_threshold_m": round(turn_on, 2) if turn_on is not None else None,
        "optimal_range": {
            "min_m": round(optimal_min, 1) if optimal_min is not None else None,
            "max_m": round(optimal_max, 1) if optimal_max is not None else None,
            "best_bin": best_bin,
            "best_mean_foam_fraction": round(best_mean, 4) if best_bin else None,
        },
        "blow_out_point_m": round(blow_out, 2) if blow_out is not None else None,
        "primary_direction": best_dir,
        "responsive_directions": responsive_dirs,
        "swell_bins": bin_means,
        "direction_bins": dir_means,
        "foam_stats": {
            "mean": round(float(np.mean(all_fracs)), 4),
            "max": round(float(np.max(all_fracs)), 4),
            "std": round(float(np.std(all_fracs)), 4),
        },
        "nir_stats": {
            "mean": round(float(np.mean(all_nirs)), 1) if all_nirs else None,
            "max": round(float(np.max(all_nirs)), 1) if all_nirs else None,
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build swell-response profiles from foam detection data."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to spot config JSON. Default: {DEFAULT_CONFIG_PATH}",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to foam detections JSON. Default: inferred from config slug.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Override output path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("Phase 2.5: Build Swell-Response Profiles")
    print("=" * 60)

    config = load_region_config(args.config)
    slug = config["slug"]

    # Load foam detections
    input_path = args.input or default_manifest_path("foam_detections", slug)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found. Run 13_detect_foam_nir.py first.")
        sys.exit(1)

    with input_path.open() as f:
        foam_data = json.load(f)

    detections = foam_data.get("detections", [])
    print(f"Spot: {config['name']} ({slug})")
    print(f"Loaded {len(detections)} foam detections from {input_path}")

    if not detections:
        print("ERROR: No detections found in input file.")
        sys.exit(1)

    # Group detections by segment_id
    by_segment: dict[str, list[dict]] = defaultdict(list)
    for det in detections:
        by_segment[det["segment_id"]].append(det)

    print(f"Segments with data: {len(by_segment)}")

    # Build profile for each segment
    profiles: dict[str, dict] = {}
    complete = 0
    insufficient = 0

    for seg_id in sorted(by_segment.keys()):
        obs = by_segment[seg_id]
        profile = build_profile(obs)
        profiles[seg_id] = profile

        if profile["status"] == "complete":
            complete += 1
            turn_on = profile.get("turn_on_threshold_m")
            opt_range = profile.get("optimal_range", {})
            blow_out = profile.get("blow_out_point_m")
            primary_dir = profile.get("primary_direction")

            turn_on_str = f"{turn_on}m" if turn_on is not None else "N/A"
            opt_str = (
                f"{opt_range.get('min_m')}-{opt_range.get('max_m')}m"
                if opt_range.get("min_m") is not None
                else "N/A"
            )
            blow_str = f"{blow_out}m" if blow_out is not None else "N/A"
            dir_str = primary_dir or "N/A"

            print(
                f"  {seg_id}: turn_on={turn_on_str}, "
                f"optimal={opt_str}, "
                f"blow_out={blow_str}, "
                f"dir={dir_str} "
                f"({profile['observation_count']} obs)"
            )
        else:
            insufficient += 1
            print(f"  {seg_id}: insufficient data ({profile['observation_count']} obs)")

    # Write output
    run_id = generate_run_id()
    output_path = args.output or default_manifest_path("swell_profiles", slug)

    payload = {
        "script": "14_build_swell_profiles.py",
        "run_id": run_id,
        "generated_at_utc": now_utc_iso(),
        "code_version": get_code_version(),
        "config": {
            "spot": config["name"],
            "slug": slug,
        },
        "parameters": {
            "foam_present_threshold": FOAM_PRESENT_THRESHOLD,
            "foam_blowout_threshold": FOAM_BLOWOUT_THRESHOLD,
            "foam_optimal_threshold": FOAM_OPTIMAL_THRESHOLD,
            "min_observations": MIN_OBSERVATIONS,
            "swell_bin_edges": SWELL_BIN_EDGES,
        },
        "input_source": str(input_path),
        "summary": {
            "total_segments": len(profiles),
            "complete_profiles": complete,
            "insufficient_data": insufficient,
            "total_detections": len(detections),
        },
        "profiles": profiles,
    }

    write_json(output_path, payload)

    print(f"\n{'=' * 60}")
    print(f"RESULTS")
    print(f"{'=' * 60}")
    print(f"Total segments: {len(profiles)}")
    print(f"Complete profiles: {complete}")
    print(f"Insufficient data: {insufficient}")

    # Summary of turn-on thresholds across segments
    turn_ons = [
        p["turn_on_threshold_m"]
        for p in profiles.values()
        if p.get("turn_on_threshold_m") is not None
    ]
    if turn_ons:
        print(f"\nTurn-on threshold distribution:")
        print(f"  Min:  {min(turn_ons):.2f}m")
        print(f"  Max:  {max(turn_ons):.2f}m")
        print(f"  Mean: {sum(turn_ons) / len(turn_ons):.2f}m")

    print(f"\nProfiles saved to {output_path}")


if __name__ == "__main__":
    main()
