#!/usr/bin/env python3
"""Build optimized static data files for the Phase 3 web viewer.

Reads pipeline data and produces compact JSON files in web/public/data/.
Simplifies the 21MB segments GeoJSON into lightweight point-based data.
"""

import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE_DATA = ROOT / "pipeline" / "data"
MANIFESTS = PIPELINE_DATA / "manifests"
WEB_DATA = ROOT / "web" / "public" / "data"
WEB_GALLERY = ROOT / "web" / "public" / "gallery"


def build_spots():
    """Copy ns_spots.geojson as-is (it's small)."""
    src = PIPELINE_DATA / "ns_spots.geojson"
    with open(src) as f:
        data = json.load(f)

    # Enrich spots with foam detection summaries and swell profile data
    for feature in data["features"]:
        slug = feature["properties"]["slug"]

        # Add foam detection summary
        foam_path = MANIFESTS / f"{slug}_foam_detections.json"
        if foam_path.exists():
            with open(foam_path) as f:
                foam = json.load(f)
            feature["properties"]["foam_summary"] = foam["summary"]
        else:
            feature["properties"]["foam_summary"] = None

        # Check if swell profile exists
        profile_path = MANIFESTS / f"{slug}_swell_profiles.json"
        feature["properties"]["has_swell_profile"] = profile_path.exists()

    out = WEB_DATA / "spots.json"
    with open(out, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"  spots.json: {len(data['features'])} spots, {out.stat().st_size / 1024:.1f}KB")


def build_segments():
    """Convert 16,939 LineString segments to lightweight centroid points.

    Full segments file is 21MB — too big for web. We create:
    1. segments-high.json: high-scoring segments (centroid points with metadata)
    2. segments-all.json: moderate+ segments (centroid points, minimal metadata)

    Prefers ns_ranked_segments.geojson (composite scores) when available,
    falls back to ns_scored_segments.geojson (geometry-only).
    """
    ranked_src = PIPELINE_DATA / "coastline" / "ns_ranked_segments.geojson"
    scored_src = PIPELINE_DATA / "coastline" / "ns_scored_segments.geojson"

    use_ranked = ranked_src.exists()
    src = ranked_src if use_ranked else scored_src
    source_label = "ranked (composite)" if use_ranked else "scored (geometry-only)"
    print(f"  Using {source_label} segments from {src.name}")

    with open(src) as f:
        data = json.load(f)

    high_features = []
    all_features = []

    # Thresholds: use composite_score when available, else total_score
    high_threshold = 50 if use_ranked else 60
    all_threshold = 30 if use_ranked else 40

    for feat in data["features"]:
        props = feat["properties"]
        # composite_score from ranked, total_score from scored
        score = props.get("composite_score") or props.get("total_score", 0)
        centroid = [props["centroid_lon"], props["centroid_lat"]]

        if score > all_threshold:
            minimal: dict = {
                "type": "Feature",
                "properties": {
                    "id": props["segment_id"],
                    "score": score,
                },
                "geometry": {"type": "Point", "coordinates": centroid},
            }
            all_features.append(minimal)

        if score > high_threshold:
            detailed: dict = {
                "type": "Feature",
                "properties": {
                    "id": props["segment_id"],
                    "score": score,
                    "swell_exposure": props.get("swell_exposure_score"),
                    "geometry_score": props.get("geometry_score"),
                    "bathymetry": props.get("bathymetry_score"),
                    "access": props.get("road_access_score"),
                    "orientation": props.get("orientation_deg"),
                    "exposure_arc": props.get("exposure_arc_deg"),
                    "rank": props.get("rank"),
                },
                "geometry": {"type": "Point", "coordinates": centroid},
            }

            # Add composite ranking fields when available
            if use_ranked:
                detailed["properties"]["composite_score"] = props.get("composite_score")
                detailed["properties"]["confidence"] = props.get("confidence")
                detailed["properties"]["foam_component"] = props.get("foam_component")
                detailed["properties"]["profile_component"] = props.get("profile_component")
                detailed["properties"]["geometry_component"] = props.get("geometry_component")
                detailed["properties"]["foam_obs_count"] = props.get("foam_obs_count")
                detailed["properties"]["turn_on_threshold"] = props.get("turn_on_threshold")
                detailed["properties"]["optimal_swell"] = props.get("optimal_swell")
                detailed["properties"]["primary_direction"] = props.get("primary_direction")

            high_features.append(detailed)

    high_out = WEB_DATA / "segments-high.json"
    all_out = WEB_DATA / "segments-all.json"

    high_geojson = {"type": "FeatureCollection", "features": high_features}
    all_geojson = {"type": "FeatureCollection", "features": all_features}

    with open(high_out, "w") as f:
        json.dump(high_geojson, f, separators=(",", ":"))
    with open(all_out, "w") as f:
        json.dump(all_geojson, f, separators=(",", ":"))

    print(f"  segments-high.json: {len(high_features)} segments (>{high_threshold}), {high_out.stat().st_size / 1024:.1f}KB")
    print(f"  segments-all.json: {len(all_features)} segments (>{all_threshold}), {all_out.stat().st_size / 1024:.1f}KB")


def build_spot_details():
    """Build per-spot detail files combining foam detections + swell profiles."""
    spots_dir = WEB_DATA / "spots"
    spots_dir.mkdir(exist_ok=True)

    src = PIPELINE_DATA / "ns_spots.geojson"
    with open(src) as f:
        spots = json.load(f)

    for feature in spots["features"]:
        slug = feature["properties"]["slug"]
        detail = {"slug": slug, "name": feature["properties"]["name"]}

        # Swell profile
        profile_path = MANIFESTS / f"{slug}_swell_profiles.json"
        if profile_path.exists():
            with open(profile_path) as f:
                profile_data = json.load(f)

            # Aggregate profiles across segments into a spot-level profile
            all_bins: dict[str, list[float]] = {}
            all_directions: dict[str, list[float]] = {}
            best_turn_on = None
            best_optimal = None
            best_blow_out = None
            total_obs = 0

            for seg_id, profile in profile_data["profiles"].items():
                if profile["status"] != "complete":
                    continue
                total_obs += profile["observation_count"]

                for bin_label, bin_data in profile["swell_bins"].items():
                    if bin_label not in all_bins:
                        all_bins[bin_label] = []
                    all_bins[bin_label].append(bin_data["mean_foam_fraction"])

                for dir_label, dir_data in profile["direction_bins"].items():
                    if dir_label not in all_directions:
                        all_directions[dir_label] = []
                    all_directions[dir_label].append(dir_data["mean_foam_fraction"])

                turn_on = profile.get("turn_on_threshold_m")
                if turn_on is not None:
                    if best_turn_on is None or turn_on < best_turn_on:
                        best_turn_on = turn_on

                opt = profile.get("optimal_range")
                if opt and opt.get("best_mean_foam_fraction"):
                    if best_optimal is None or opt["best_mean_foam_fraction"] > best_optimal.get("best_mean_foam_fraction", 0):
                        best_optimal = opt

                blow = profile.get("blow_out_point_m")
                if blow is not None:
                    if best_blow_out is None or blow > best_blow_out:
                        best_blow_out = blow

            # Average across segments for each bin
            swell_bins = {}
            for label, fractions in sorted(all_bins.items()):
                swell_bins[label] = round(sum(fractions) / len(fractions), 4)

            direction_bins = {}
            for label, fractions in sorted(all_directions.items()):
                direction_bins[label] = round(sum(fractions) / len(fractions), 4)

            detail["swell_profile"] = {
                "swell_bins": swell_bins,
                "direction_bins": direction_bins,
                "turn_on_threshold_m": best_turn_on,
                "optimal_range": best_optimal,
                "blow_out_point_m": best_blow_out,
                "total_observations": total_obs,
                "segment_count": profile_data["summary"]["complete_profiles"],
            }
        else:
            detail["swell_profile"] = None

        # Foam detection summary
        foam_path = MANIFESTS / f"{slug}_foam_detections.json"
        if foam_path.exists():
            with open(foam_path) as f:
                foam_data = json.load(f)
            detail["foam_summary"] = foam_data["summary"]
        else:
            detail["foam_summary"] = None

        out = spots_dir / f"{slug}.json"
        with open(out, "w") as f:
            json.dump(detail, f, separators=(",", ":"))

    slugs = [f["properties"]["slug"] for f in spots["features"]]
    print(f"  spot details: {len(slugs)} files in spots/")


def build_gallery():
    """Copy gallery manifest and symlink/copy images."""
    gallery_src = PIPELINE_DATA / "gallery"
    manifest_src = gallery_src / "manifest.json"

    if not manifest_src.exists():
        print("  gallery: no manifest found, skipping")
        return

    with open(manifest_src) as f:
        manifest = json.load(f)

    # Copy images to web/public/gallery/
    for spot in manifest["spots"]:
        slug = spot["slug"]
        spot_gallery_dir = WEB_GALLERY / slug
        spot_gallery_dir.mkdir(parents=True, exist_ok=True)

        for scene in spot["scenes"]:
            for key in ("rgb_path", "nir_path", "annotated_rgb_path", "annotated_nir_path"):
                src_val = scene.get(key)
                if not src_val:
                    scene[key] = None
                    continue
                src_path = ROOT / src_val
                if src_path.exists():
                    dst = spot_gallery_dir / src_path.name
                    shutil.copy2(src_path, dst)
                    # Update path to be web-relative
                    scene[key] = f"/gallery/{slug}/{src_path.name}"
                else:
                    scene[key] = None

    out = WEB_DATA / "gallery.json"
    with open(out, "w") as f:
        json.dump(manifest, f, separators=(",", ":"))

    total_images = sum(len(s["scenes"]) * 2 for s in manifest["spots"])
    print(f"  gallery.json: {len(manifest['spots'])} spots, ~{total_images} images, {out.stat().st_size / 1024:.1f}KB")


def main():
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    WEB_GALLERY.mkdir(parents=True, exist_ok=True)

    print("Building web data...")
    build_spots()
    build_segments()
    build_spot_details()
    build_gallery()
    print("Done!")


if __name__ == "__main__":
    main()
