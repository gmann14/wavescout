#!/usr/bin/env python3
"""Build optimized static data files for the Phase 3 web viewer.

Reads pipeline data and produces compact JSON files in web/public/data/.
Simplifies the 21MB segments GeoJSON into lightweight point-based data.
"""

import json
import shutil
from pathlib import Path

from _public_dataset import (
    confidence_label_for_level,
    derive_evidence_confidence_level,
    derive_spot_publication_status,
    derive_spot_verification_status,
    normalize_break_type,
    quality_status_from_score,
    validate_public_dataset,
    write_dataset_manifest,
)

ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE_DATA = ROOT / "pipeline" / "data"
MANIFESTS = PIPELINE_DATA / "manifests"
WEB_DATA = ROOT / "web" / "public" / "data"
WEB_GALLERY = ROOT / "web" / "public" / "gallery"


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _ranking_provenance() -> dict:
    ranking_manifest = MANIFESTS / "unified_ranking_manifest.json"
    if ranking_manifest.exists():
        data = _load_json(ranking_manifest)
        return {
            "run_id": data.get("run_id", "unknown"),
            "generated_at_utc": data.get("generated_at_utc", "unknown"),
            "code_version": data.get("code_version", "unknown"),
            "config_version": "unknown",
        }
    gallery_manifest = PIPELINE_DATA / "gallery" / "manifest.json"
    if gallery_manifest.exists():
        data = _load_json(gallery_manifest)
        return {
            "run_id": data.get("run_id", "unknown"),
            "generated_at_utc": data.get("generated_at_utc", "unknown"),
            "code_version": data.get("code_version", "unknown"),
            "config_version": "unknown",
        }
    return {
        "run_id": "unknown",
        "generated_at_utc": "unknown",
        "code_version": "unknown",
        "config_version": "unknown",
    }


def _spot_gallery_summaries() -> dict[str, dict]:
    manifest_src = PIPELINE_DATA / "gallery" / "manifest.json"
    if not manifest_src.exists():
        return {}

    manifest = _load_json(manifest_src)
    by_slug: dict[str, dict] = {}
    for spot in manifest.get("spots", []):
        scenes = spot.get("scenes", [])
        quality_scores = [scene.get("quality_score") for scene in scenes if scene.get("quality_score") is not None]
        usable = sum(1 for score in quality_scores if score >= 90)
        degraded = sum(1 for score in quality_scores if score is not None and 60 <= score < 90)
        latest = max((scene.get("date") for scene in scenes if scene.get("date")), default=None)
        by_slug[spot["slug"]] = {
            "scene_count": len(scenes),
            "usable_scene_count": usable,
            "degraded_scene_count": degraded,
            "latest_scene_date": latest,
        }
    return by_slug


def _spot_source_index() -> dict[str, dict]:
    src = PIPELINE_DATA / "ns_spots.geojson"
    data = _load_json(src)
    index: dict[str, dict] = {}
    for feature in data.get("features", []):
        slug = feature.get("properties", {}).get("slug")
        if slug:
            index[slug] = feature
    return index


def _is_public_spot(feature: dict) -> bool:
    publication_status = derive_spot_publication_status(feature.get("properties", {}).get("source"))
    return publication_status != "internal_only"


def _spot_explanation(feature: dict, surf_potential_score: float, has_profile: bool) -> dict:
    notes = feature["properties"].get("notes", "")
    return {
        "summary": notes or "Known reference location included for calibration and browsing.",
        "score_components": {
            "geometry": 0.0,
            "foam": round(surf_potential_score * 0.7, 1),
            "profile": round(surf_potential_score * 0.3, 1) if has_profile else 0.0,
        },
        "highlights": [
            "Reference location in the Nova Scotia dataset",
            "Imagery evidence available" if feature["properties"].get("foam_summary") else "Metadata-only reference",
        ],
        "caveats": [
            "Score is a reference-entry proxy until the web app migrates to normalized ranking semantics.",
        ],
        "provenance": _ranking_provenance(),
    }


def build_spots():
    """Copy ns_spots.geojson as-is (it's small)."""
    src = PIPELINE_DATA / "ns_spots.geojson"
    data = _load_json(src)
    data["features"] = [feature for feature in data.get("features", []) if _is_public_spot(feature)]
    gallery_summaries = _spot_gallery_summaries()

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
        has_profile = profile_path.exists()
        feature["properties"]["has_swell_profile"] = has_profile

        legacy_confidence = feature["properties"].get("confidence")
        confidence_level = derive_evidence_confidence_level(legacy_confidence)
        foam_summary = feature["properties"].get("foam_summary") or {}
        scenes_processed = foam_summary.get("scenes_processed", 0) or 0
        scenes_with_foam = foam_summary.get("scenes_with_foam", 0) or 0
        surf_potential_score = round((scenes_with_foam / scenes_processed) * 100, 1) if scenes_processed else 0.0
        mean_quality = ((foam_summary.get("quality") or {}).get("mean_quality_score"))

        feature["properties"]["break_type"] = normalize_break_type(feature["properties"].get("type"))
        feature["properties"]["verification_status"] = derive_spot_verification_status(
            feature["properties"].get("source"),
            legacy_confidence,
        )
        feature["properties"]["publication_status"] = derive_spot_publication_status(
            feature["properties"].get("source")
        )
        feature["properties"]["source_summary"] = feature["properties"].get("source", "unknown")
        feature["properties"]["short_summary"] = feature["properties"].get("notes", "")
        feature["properties"]["surf_potential_score"] = surf_potential_score
        feature["properties"]["evidence_confidence_level"] = confidence_level
        feature["properties"]["evidence_confidence_label"] = confidence_label_for_level(confidence_level)
        feature["properties"]["gallery_available"] = gallery_summaries.get(slug, {}).get("scene_count", 0) > 0
        feature["properties"]["swell_profile_available"] = has_profile
        feature["properties"]["quality_status"] = quality_status_from_score(mean_quality)
        feature["properties"]["swell_window_summary"] = feature["properties"].get("swell_window", "")
        feature["properties"]["explanation"] = _spot_explanation(feature, surf_potential_score, has_profile)

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
            evidence_level = derive_evidence_confidence_level(props.get("confidence", 0))
            minimal: dict = {
                "type": "Feature",
                "properties": {
                    "id": props["segment_id"],
                    "score": score,
                    "surf_potential_score": score,
                    "evidence_confidence_level": evidence_level,
                },
                "geometry": {"type": "Point", "coordinates": centroid},
            }
            all_features.append(minimal)

        if score > high_threshold:
            evidence_level = derive_evidence_confidence_level(props.get("confidence", 0))
            geometry_component = props.get("geometry_component") or round(score, 1)
            foam_component = props.get("foam_component") or 0.0
            profile_component = props.get("profile_component") or 0.0
            explanation = props.get("explanation") or {}
            detailed: dict = {
                "type": "Feature",
                "properties": {
                    "id": props["segment_id"],
                    "score": score,
                    "verification_status": "candidate",
                    "publication_status": "public_coarse",
                    "surf_potential_score": score,
                    "evidence_confidence_level": evidence_level,
                    "evidence_confidence_label": confidence_label_for_level(evidence_level),
                    "quality_status": "usable" if evidence_level >= 2 else "degraded",
                    "score_components": {
                        "geometry": geometry_component,
                        "foam": foam_component,
                        "profile": profile_component,
                    },
                    "swell_exposure": props.get("swell_exposure_score"),
                    "geometry_score": props.get("geometry_score"),
                    "bathymetry": props.get("bathymetry_score"),
                    "access": props.get("road_access_score"),
                    "orientation": props.get("orientation_deg"),
                    "exposure_arc": props.get("exposure_arc_deg"),
                    "rank": props.get("rank"),
                    "turn_on_threshold_m": props.get("turn_on_threshold"),
                    "optimal_swell_range": props.get("optimal_swell"),
                    "explanation": {
                        "summary": explanation.get("summary", "Candidate segment in the ranked coastline dataset."),
                        "score_components": {
                            "geometry": geometry_component,
                            "foam": foam_component,
                            "profile": profile_component,
                        },
                        "highlights": explanation.get("highlights", []),
                        "caveats": explanation.get("caveats", []),
                        "provenance": _ranking_provenance(),
                    },
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
    if spots_dir.exists():
        shutil.rmtree(spots_dir)
    spots_dir.mkdir(parents=True, exist_ok=True)

    src = PIPELINE_DATA / "ns_spots.geojson"
    spots = _load_json(src)
    spots["features"] = [feature for feature in spots.get("features", []) if _is_public_spot(feature)]
    gallery_summaries = _spot_gallery_summaries()

    for feature in spots["features"]:
        slug = feature["properties"]["slug"]
        legacy_confidence = feature["properties"].get("confidence")
        confidence_level = derive_evidence_confidence_level(legacy_confidence)
        detail = {
            "slug": slug,
            "name": feature["properties"]["name"],
            "verification_status": derive_spot_verification_status(feature["properties"].get("source"), legacy_confidence),
            "publication_status": derive_spot_publication_status(feature["properties"].get("source")),
            "evidence_confidence_level": confidence_level,
            "evidence_confidence_label": confidence_label_for_level(confidence_level),
        }

        # Swell profile
        profile_path = MANIFESTS / f"{slug}_swell_profiles.json"
        has_profile = profile_path.exists()
        if profile_path.exists():
            profile_data = _load_json(profile_path)

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
            foam_data = _load_json(foam_path)
            detail["foam_summary"] = foam_data["summary"]
        else:
            detail["foam_summary"] = None

        foam_summary = detail["foam_summary"] or {}
        scenes_processed = foam_summary.get("scenes_processed", 0) or 0
        scenes_with_foam = foam_summary.get("scenes_with_foam", 0) or 0
        surf_potential_score = round((scenes_with_foam / scenes_processed) * 100, 1) if scenes_processed else 0.0
        mean_quality = ((foam_summary.get("quality") or {}).get("mean_quality_score"))
        detail["surf_potential_score"] = surf_potential_score
        detail["quality_status"] = quality_status_from_score(mean_quality)
        detail["gallery_summary"] = gallery_summaries.get(
            slug,
            {
                "scene_count": 0,
                "usable_scene_count": 0,
                "degraded_scene_count": 0,
                "latest_scene_date": None,
            },
        )
        detail["provenance"] = _ranking_provenance()
        detail["explanation"] = _spot_explanation(feature, surf_potential_score, has_profile)

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

    manifest = _load_json(manifest_src)
    spot_index = _spot_source_index()

    if WEB_GALLERY.exists():
        shutil.rmtree(WEB_GALLERY)
    WEB_GALLERY.mkdir(parents=True, exist_ok=True)

    public_spots = []
    total_images = 0

    # Copy images to web/public/gallery/
    for spot in manifest["spots"]:
        slug = spot["slug"]
        source_feature = spot_index.get(slug)
        source = source_feature.get("properties", {}).get("source") if source_feature else spot.get("source")
        publication_status = derive_spot_publication_status(source)
        if publication_status == "internal_only":
            continue

        spot["publication_status"] = publication_status
        spot_gallery_dir = WEB_GALLERY / slug
        spot_gallery_dir.mkdir(parents=True, exist_ok=True)

        for scene in spot["scenes"]:
            scene["scene_id"] = f"{slug}:{scene['date']}"
            scene["quality_status"] = quality_status_from_score(scene.get("quality_score"))
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
                    total_images += 1
                else:
                    scene[key] = None

        public_spots.append(spot)

    manifest["spots"] = public_spots
    if isinstance(manifest.get("summary"), dict):
        manifest["summary"]["total_spots"] = len(public_spots)
        manifest["summary"]["total_images"] = total_images

    out = WEB_DATA / "gallery.json"
    with open(out, "w") as f:
        json.dump(manifest, f, separators=(",", ":"))

    print(f"  gallery.json: {len(manifest['spots'])} spots, ~{total_images} images, {out.stat().st_size / 1024:.1f}KB")


def main():
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    WEB_GALLERY.mkdir(parents=True, exist_ok=True)

    print("Building web data...")
    build_spots()
    build_segments()
    build_spot_details()
    build_gallery()
    manifest_path = write_dataset_manifest()
    validate_public_dataset(strict=False, require_atlas=False)
    print(f"  dataset-manifest.json: {manifest_path.stat().st_size / 1024:.1f}KB")
    print("Done!")


if __name__ == "__main__":
    main()
