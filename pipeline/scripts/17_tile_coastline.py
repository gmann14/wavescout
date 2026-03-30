#!/usr/bin/env python3
"""Script 17: Tile coastline into ~3km browsable atlas sections.

Groups the 16,939 scored coastline segments into ~3km sections by walking
along the actual coastline geometry. Each section contains ~6 consecutive
segments (500m stride) and gets a bounding box, centroid, and score summary.

Usage:
    python3 pipeline/scripts/17_tile_coastline.py
    python3 pipeline/scripts/17_tile_coastline.py --min-score 50
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, MultiLineString, Point, box
from shapely.ops import linemerge, nearest_points
from shapely.strtree import STRtree

from _script_utils import generate_run_id, get_code_version, now_utc_iso, write_json

# --- Paths ---
COASTLINE_PATH = Path("pipeline/data/coastline/ns_coastline.geojson")
SEGMENTS_PATH = Path("pipeline/data/coastline/ns_scored_segments.geojson")
ATLAS_DIR = Path("pipeline/data/atlas")
ATLAS_CONFIGS_DIR = Path("pipeline/configs/atlas")

# --- Constants ---
SECTION_LENGTH_M = 3000  # Target section length (~3km)
SEGMENTS_PER_SECTION = 6  # ~6 segments at 500m stride = 3km
OVERLAP_SEGMENTS = 1  # 1 segment overlap between sections
MIN_SEGMENT_SCORE = 40  # Only include sections with at least 1 segment > this
BBOX_PADDING_DEG = 0.003  # ~300m padding around section bbox for imagery


def load_coastline(path: Path) -> list[LineString]:
    """Load coastline LineStrings from GeoJSON."""
    with open(path) as f:
        data = json.load(f)

    lines = []
    for feat in data["features"]:
        geom = feat["geometry"]
        if geom["type"] == "LineString":
            coords = geom["coordinates"]
            if len(coords) >= 2:
                lines.append(LineString(coords))
    return lines


def merge_coastline(lines: list[LineString]) -> list[LineString]:
    """Merge connected coastline segments into longer chains.

    Uses shapely linemerge to join LineStrings that share endpoints,
    then splits the result back into individual LineStrings.
    """
    print(f"  Merging {len(lines)} raw coastline segments...", end=" ", flush=True)
    merged = linemerge(MultiLineString(lines))

    if isinstance(merged, LineString):
        result = [merged]
    elif isinstance(merged, MultiLineString):
        result = list(merged.geoms)
    else:
        result = [g for g in merged.geoms if isinstance(g, LineString)]

    # Filter out very short chains (< 500m in degrees, roughly)
    MIN_LENGTH_DEG = 0.003  # ~300m
    result = [line for line in result if line.length > MIN_LENGTH_DEG]

    print(f"{len(result)} chains")
    return result


def load_segments(path: Path) -> list[dict]:
    """Load scored segments from GeoJSON."""
    with open(path) as f:
        data = json.load(f)

    segments = []
    for feat in data["features"]:
        props = feat["properties"]
        segments.append({
            "segment_id": props["segment_id"],
            "centroid_lat": props["centroid_lat"],
            "centroid_lon": props["centroid_lon"],
            "total_score": props["total_score"],
            "swell_exposure_score": props.get("swell_exposure_score", 0),
            "geometry_score": props.get("geometry_score", 0),
            "orientation_deg": props.get("orientation_deg", 0),
            "exposure_arc_deg": props.get("exposure_arc_deg", 0),
            "rank": props.get("rank"),
        })
    return segments


def assign_segments_to_chains(
    chains: list[LineString],
    segments: list[dict],
    max_dist_deg: float = 0.01,
) -> dict[int, list[tuple[float, dict]]]:
    """Assign each segment to its nearest coastline chain.

    Returns {chain_index: [(distance_along_chain, segment_dict), ...]} sorted
    by distance along chain.
    """
    print(f"  Assigning {len(segments)} segments to {len(chains)} chains...", end=" ", flush=True)

    # Build spatial index for chains
    tree = STRtree(chains)

    chain_segments: dict[int, list[tuple[float, dict]]] = defaultdict(list)
    assigned = 0

    for seg in segments:
        pt = Point(seg["centroid_lon"], seg["centroid_lat"])

        # Find nearest chain
        idx = tree.nearest(pt)
        chain = chains[idx]
        dist = chain.distance(pt)

        if dist > max_dist_deg:
            continue

        # Project segment onto chain to get distance along it
        frac = chain.project(pt, normalized=True)
        chain_segments[idx].append((frac, seg))
        assigned += 1

    # Sort segments along each chain by their position
    for idx in chain_segments:
        chain_segments[idx].sort(key=lambda x: x[0])

    print(f"{assigned} assigned")
    return chain_segments


def tile_chain_into_sections(
    chain_idx: int,
    chain: LineString,
    ordered_segments: list[tuple[float, dict]],
    section_counter: int,
) -> tuple[list[dict], int]:
    """Tile a single coastline chain into ~3km sections.

    Walks along the chain grouping segments into sections of SEGMENTS_PER_SECTION,
    with OVERLAP_SEGMENTS overlap.
    """
    sections = []
    stride = SEGMENTS_PER_SECTION - OVERLAP_SEGMENTS  # 5 segments per step
    n = len(ordered_segments)

    if n == 0:
        return sections, section_counter

    i = 0
    while i < n:
        end = min(i + SEGMENTS_PER_SECTION, n)
        group = ordered_segments[i:end]

        if len(group) < 2:
            i += stride
            continue

        seg_dicts = [s for _, s in group]

        # Compute section properties
        lats = [s["centroid_lat"] for s in seg_dicts]
        lons = [s["centroid_lon"] for s in seg_dicts]
        scores = [s["total_score"] for s in seg_dicts]

        centroid_lat = sum(lats) / len(lats)
        centroid_lon = sum(lons) / len(lons)
        mean_score = round(sum(scores) / len(scores), 1)
        max_score = max(scores)

        # Bbox from segment centroids + padding
        min_lon = min(lons) - BBOX_PADDING_DEG
        max_lon = max(lons) + BBOX_PADDING_DEG
        min_lat = min(lats) - BBOX_PADDING_DEG
        max_lat = max(lats) + BBOX_PADDING_DEG

        # Estimate coastline length from positions along chain
        frac_start = group[0][0]
        frac_end = group[-1][0]
        length_m = (frac_end - frac_start) * chain.length * 111_000  # rough deg→m

        section_counter += 1
        section_id = f"atlas-{section_counter:04d}"

        sections.append({
            "section_id": section_id,
            "chain_index": chain_idx,
            "centroid_lat": round(centroid_lat, 6),
            "centroid_lon": round(centroid_lon, 6),
            "bbox": [round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)],
            "mean_score": mean_score,
            "max_score": max_score,
            "segment_count": len(seg_dicts),
            "segment_ids": [s["segment_id"] for s in seg_dicts],
            "coastline_length_m": round(max(length_m, len(seg_dicts) * 250), 0),
        })

        i += stride

    return sections, section_counter


def build_section_geojson(sections: list[dict]) -> dict:
    """Build GeoJSON FeatureCollection with section bboxes as polygons."""
    features = []
    for sec in sections:
        bbox = sec["bbox"]
        # Create polygon from bbox
        polygon_coords = [
            [bbox[0], bbox[1]],
            [bbox[2], bbox[1]],
            [bbox[2], bbox[3]],
            [bbox[0], bbox[3]],
            [bbox[0], bbox[1]],
        ]
        features.append({
            "type": "Feature",
            "properties": {
                "section_id": sec["section_id"],
                "centroid_lat": sec["centroid_lat"],
                "centroid_lon": sec["centroid_lon"],
                "mean_score": sec["mean_score"],
                "max_score": sec["max_score"],
                "segment_count": sec["segment_count"],
                "segment_ids": sec["segment_ids"],
                "coastline_length_m": sec["coastline_length_m"],
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon_coords],
            },
        })
    return {"type": "FeatureCollection", "features": features}


def build_section_config(sec: dict) -> dict:
    """Build a spot-format config for an atlas section."""
    return {
        "name": f"Atlas Section {sec['section_id']}",
        "slug": sec["section_id"],
        "region": "nova-scotia",
        "bbox": sec["bbox"],
        "point": {
            "lat": sec["centroid_lat"],
            "lon": sec["centroid_lon"],
        },
        "date_range": {"start": "2021-10-01"},
        "export": {"drive_folder": "wavescout_atlas"},
        "atlas_metadata": {
            "mean_score": sec["mean_score"],
            "max_score": sec["max_score"],
            "segment_count": sec["segment_count"],
            "segment_ids": sec["segment_ids"],
            "coastline_length_m": sec["coastline_length_m"],
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Tile coastline into atlas sections")
    parser.add_argument(
        "--min-score",
        type=float,
        default=MIN_SEGMENT_SCORE,
        help=f"Min segment score to include a section (default: {MIN_SEGMENT_SCORE})",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Script 17: Tile Coastline into Atlas Sections")
    print("=" * 60)

    # Load data
    print("\nLoading data...")
    if not COASTLINE_PATH.exists():
        print(f"ERROR: {COASTLINE_PATH} not found")
        sys.exit(1)
    if not SEGMENTS_PATH.exists():
        print(f"ERROR: {SEGMENTS_PATH} not found")
        sys.exit(1)

    coastline_lines = load_coastline(COASTLINE_PATH)
    print(f"  Coastline: {len(coastline_lines)} LineStrings")

    segments = load_segments(SEGMENTS_PATH)
    print(f"  Segments: {len(segments)} scored segments")

    # Merge coastline into longer chains
    print("\nProcessing coastline...")
    chains = merge_coastline(coastline_lines)

    # Sort chains by length (process longest first)
    chains_with_idx = sorted(enumerate(chains), key=lambda x: -x[1].length)
    chain_lengths = [c.length * 111_000 for _, c in chains_with_idx]
    print(f"  Longest chain: ~{chain_lengths[0]:.0f}m, median: ~{np.median(chain_lengths):.0f}m")

    # Re-index chains after sorting
    sorted_chains = [c for _, c in chains_with_idx]
    original_indices = [i for i, _ in chains_with_idx]

    # Assign segments to chains
    print("\nAssigning segments to coastline chains...")
    chain_segments = assign_segments_to_chains(sorted_chains, segments)

    # Report assignment
    total_assigned = sum(len(v) for v in chain_segments.values())
    chains_with_segs = len(chain_segments)
    print(f"  {total_assigned}/{len(segments)} segments assigned to {chains_with_segs} chains")

    # Tile each chain into sections
    print("\nTiling into sections...")
    all_sections: list[dict] = []
    section_counter = 0

    for chain_idx, chain in enumerate(sorted_chains):
        if chain_idx not in chain_segments:
            continue

        ordered = chain_segments[chain_idx]
        new_sections, section_counter = tile_chain_into_sections(
            chain_idx, chain, ordered, section_counter,
        )
        all_sections.extend(new_sections)

    print(f"  Total sections before filtering: {len(all_sections)}")

    # Filter: only sections with at least 1 segment scoring > min_score
    filtered = [
        sec for sec in all_sections
        if sec["max_score"] > args.min_score
    ]
    print(f"  After filtering (max_score > {args.min_score}): {len(filtered)}")

    # Sort by section_id
    filtered.sort(key=lambda x: x["section_id"])

    # Reassign section IDs after filtering
    for i, sec in enumerate(filtered, 1):
        sec["section_id"] = f"atlas-{i:04d}"

    # Output: GeoJSON
    ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    geojson = build_section_geojson(filtered)
    geojson_path = ATLAS_DIR / "ns_atlas_sections.geojson"
    write_json(geojson_path, geojson)
    print(f"\n  GeoJSON: {geojson_path} ({len(filtered)} sections)")

    # Output: per-section configs
    ATLAS_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    for sec in filtered:
        config = build_section_config(sec)
        config_path = ATLAS_CONFIGS_DIR / f"{sec['section_id']}.json"
        write_json(config_path, config)
    print(f"  Configs: {ATLAS_CONFIGS_DIR}/ ({len(filtered)} files)")

    # Output: manifest
    manifest = {
        "script": "17_tile_coastline.py",
        "run_id": generate_run_id(),
        "generated_at_utc": now_utc_iso(),
        "code_version": get_code_version(),
        "parameters": {
            "section_length_m": SECTION_LENGTH_M,
            "segments_per_section": SEGMENTS_PER_SECTION,
            "overlap_segments": OVERLAP_SEGMENTS,
            "min_segment_score": args.min_score,
            "bbox_padding_deg": BBOX_PADDING_DEG,
        },
        "summary": {
            "total_sections": len(filtered),
            "total_segments_covered": sum(s["segment_count"] for s in filtered),
            "mean_section_score": round(
                sum(s["mean_score"] for s in filtered) / len(filtered), 1
            ) if filtered else 0,
        },
    }
    manifest_path = ATLAS_DIR / "manifest.json"
    write_json(manifest_path, manifest)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Summary:")
    print(f"  Total sections: {len(filtered)}")
    print(f"  Segments covered: {sum(s['segment_count'] for s in filtered)}")

    scores = [s["mean_score"] for s in filtered]
    if scores:
        print(f"  Score distribution:")
        print(f"    Mean: {np.mean(scores):.1f}")
        print(f"    Median: {np.median(scores):.1f}")
        print(f"    Min: {min(scores):.1f}, Max: {max(scores):.1f}")
        for threshold in [40, 50, 60, 70]:
            count = sum(1 for s in scores if s >= threshold)
            print(f"    >= {threshold}: {count} sections")

    # Geographic coverage
    if filtered:
        all_lats = [s["centroid_lat"] for s in filtered]
        all_lons = [s["centroid_lon"] for s in filtered]
        print(f"  Geographic extent:")
        print(f"    Lat: {min(all_lats):.3f} to {max(all_lats):.3f}")
        print(f"    Lon: {min(all_lons):.3f} to {max(all_lons):.3f}")

    print(f"\nDone! Atlas sections ready at {ATLAS_DIR}/")


if __name__ == "__main__":
    main()
