#!/usr/bin/env python3
"""Helpers for public web dataset manifests and contract validation."""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE_DATA = ROOT / "pipeline" / "data"
MANIFESTS = PIPELINE_DATA / "manifests"
WEB_DATA = ROOT / "web" / "public" / "data"

SUPPORTED_STATUSES = {"draft", "promoted", "retired"}
CONFIDENCE_LABELS = {"none", "low", "moderate", "high"}
VERIFICATION_STATUSES = {"confirmed", "candidate", "rejected"}
PUBLICATION_STATUSES = {"public_named", "public_coarse", "internal_only"}
BREAK_TYPES = {"beach", "point", "reef", "slab", "mixed", "unknown"}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def _maybe_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _source_manifest_paths() -> dict[str, str]:
    paths: dict[str, str] = {}
    candidates = {
        "ranking": MANIFESTS / "unified_ranking_manifest.json",
        "feasibility": MANIFESTS / "feasibility_run.json",
        "gallery": PIPELINE_DATA / "gallery" / "manifest.json",
        "atlas_gallery": PIPELINE_DATA / "atlas" / "gallery" / "manifest.json",
    }
    for key, path in candidates.items():
        if path.exists():
            paths[key] = str(path.relative_to(ROOT))
    return paths


def _artifact_paths() -> dict[str, str]:
    artifacts = {
        "spots": "/data/spots.json",
        "segments_high": "/data/segments-high.json",
        "segments_all": "/data/segments-all.json",
        "gallery": "/data/gallery.json",
        "methodology": "/data/methodology.md",
        "spot_details_dir": "/data/spots/",
    }
    atlas_sections = WEB_DATA / "atlas" / "sections.json"
    atlas_gallery = WEB_DATA / "atlas" / "gallery.json"
    if atlas_sections.exists():
        artifacts["atlas_sections"] = "/data/atlas/sections.json"
    if atlas_gallery.exists():
        artifacts["atlas_gallery"] = "/data/atlas/gallery.json"
    return artifacts


def normalize_break_type(raw: str | None) -> str:
    if not raw:
        return "unknown"
    normalized = raw.strip().lower()
    if normalized in BREAK_TYPES:
        return normalized
    if "/" in normalized or "," in normalized:
        return "mixed"
    return "unknown"


def derive_evidence_confidence_level(value: Any) -> int:
    if isinstance(value, int):
        return max(0, min(3, value))
    if not isinstance(value, str):
        return 0
    normalized = value.strip().lower()
    if normalized == "high":
        return 3
    if normalized == "medium":
        return 2
    if normalized in {"low-medium", "medium-low"}:
        return 1
    if normalized == "low":
        return 1
    return 0


def confidence_label_for_level(level: int) -> str:
    return {
        0: "none",
        1: "low",
        2: "moderate",
        3: "high",
    }.get(level, "none")


def quality_status_from_score(score: float | int | None) -> str:
    if score is None:
        return "degraded"
    if score >= 90:
        return "usable"
    if score >= 60:
        return "degraded"
    return "rejected"


def derive_spot_publication_status(source: str | None) -> str:
    if source == "graham-local-knowledge":
        return "internal_only"
    return "public_named"


def derive_spot_verification_status(source: str | None, legacy_confidence: Any) -> str:
    if source == "graham-local-knowledge":
        return "confirmed"
    if derive_evidence_confidence_level(legacy_confidence) == 0:
        return "candidate"
    return "confirmed"


def build_dataset_manifest() -> dict[str, Any]:
    ranking = _maybe_manifest(MANIFESTS / "unified_ranking_manifest.json")
    gallery = _maybe_manifest(PIPELINE_DATA / "gallery" / "manifest.json")
    atlas = _maybe_manifest(PIPELINE_DATA / "atlas" / "gallery" / "manifest.json")

    run_id = (
        (ranking or {}).get("run_id")
        or (gallery or {}).get("run_id")
        or (atlas or {}).get("run_id")
        or "unknown"
    )
    code_version = (
        (ranking or {}).get("code_version")
        or (gallery or {}).get("code_version")
        or (atlas or {}).get("code_version")
        or "unknown"
    )

    return {
        "dataset_id": f"ns-{run_id}",
        "region": "Nova Scotia",
        "status": "draft",
        "run_id": run_id,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "code_version": code_version,
        "config_version": "unknown",
        "source_manifests": _source_manifest_paths(),
        "artifacts": _artifact_paths(),
    }


def write_dataset_manifest() -> Path:
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    manifest = build_dataset_manifest()
    out = WEB_DATA / "dataset-manifest.json"
    with out.open("w") as handle:
        json.dump(manifest, handle, separators=(",", ":"))
    return out


def _require_keys(obj: dict[str, Any], required: set[str], context: str) -> None:
    missing = required - set(obj)
    if missing:
        raise ValueError(f"{context} missing required keys: {sorted(missing)}")


def validate_dataset_manifest(manifest: dict[str, Any], *, require_atlas: bool = False) -> None:
    _require_keys(
        manifest,
        {
            "dataset_id",
            "region",
            "status",
            "run_id",
            "generated_at_utc",
            "code_version",
            "config_version",
            "source_manifests",
            "artifacts",
        },
        "dataset-manifest.json",
    )
    if manifest["status"] not in SUPPORTED_STATUSES:
        raise ValueError("dataset-manifest.json has unsupported status")
    artifacts = manifest["artifacts"]
    _require_keys(
        artifacts,
        {"spots", "segments_high", "segments_all", "gallery", "methodology", "spot_details_dir"},
        "dataset-manifest artifacts",
    )
    if require_atlas:
        _require_keys(artifacts, {"atlas_sections", "atlas_gallery"}, "dataset-manifest artifacts")


def validate_spots_payload(payload: dict[str, Any], *, strict: bool = False) -> None:
    if payload.get("type") != "FeatureCollection":
        raise ValueError("spots.json must be a GeoJSON FeatureCollection")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("spots.json features must be a list")
    if not features:
        return

    for feature in features:
        props = feature.get("properties", {})
        publication_status = props.get("publication_status")
        if publication_status == "internal_only":
            raise ValueError("spots.json must not expose internal_only spots")
        if publication_status not in PUBLICATION_STATUSES:
            raise ValueError("spots.json has unsupported publication_status")
        verification_status = props.get("verification_status")
        if verification_status is not None and verification_status not in VERIFICATION_STATUSES:
            raise ValueError("spots.json has unsupported verification_status")
        confidence_label = props.get("evidence_confidence_label")
        if confidence_label is not None and confidence_label not in CONFIDENCE_LABELS:
            raise ValueError("spots.json has unsupported evidence_confidence_label")

    if not strict:
        return

    props = features[0].get("properties", {})
    _require_keys(
        props,
        {
            "name",
            "slug",
            "break_type",
            "verification_status",
            "publication_status",
            "source_summary",
            "short_summary",
            "surf_potential_score",
            "evidence_confidence_level",
            "evidence_confidence_label",
            "gallery_available",
            "swell_profile_available",
            "quality_status",
            "foam_summary",
            "explanation",
        },
        "spots.json feature.properties",
    )
    if "confidence" in props:
        raise ValueError("spots.json must not expose legacy confidence in strict mode")


def validate_segments_high_payload(payload: dict[str, Any], *, strict: bool = False) -> None:
    if payload.get("type") != "FeatureCollection":
        raise ValueError("segments-high.json must be a GeoJSON FeatureCollection")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("segments-high.json features must be a list")
    if not strict or not features:
        return

    props = features[0].get("properties", {})
    _require_keys(
        props,
        {
            "id",
            "verification_status",
            "publication_status",
            "surf_potential_score",
            "evidence_confidence_level",
            "evidence_confidence_label",
            "quality_status",
            "score_components",
            "foam_obs_count",
            "turn_on_threshold_m",
            "optimal_swell_range",
            "primary_direction",
            "explanation",
        },
        "segments-high.json feature.properties",
    )


def validate_gallery_payload(payload: dict[str, Any], *, strict: bool = False) -> None:
    _require_keys(
        payload,
        {"run_id", "generated_at_utc", "code_version", "parameters", "spots", "summary"},
        "gallery.json",
    )
    spots = payload.get("spots", [])
    for spot in spots:
        publication_status = spot.get("publication_status")
        if publication_status == "internal_only":
            raise ValueError("gallery.json must not expose internal_only spots")
        if publication_status is not None and publication_status not in PUBLICATION_STATUSES:
            raise ValueError("gallery.json has unsupported publication_status")

    if not strict:
        return

    if not spots:
        raise ValueError("gallery.json must contain at least one spot in strict mode")
    spot = spots[0]
    _require_keys(spot, {"spot_name", "slug", "publication_status", "scenes"}, "gallery.json spot entry")
    scenes = spot.get("scenes", [])
    if not scenes:
        raise ValueError("gallery.json spot entry must contain at least one scene in strict mode")
    scene = scenes[0]
    _require_keys(
        scene,
        {
            "date",
            "scene_id",
            "quality_status",
            "quality_score",
            "swell_height_m",
            "swell_period_s",
            "swell_direction_deg",
            "cloud_pct",
            "foam_fraction",
            "bin_label",
            "rgb_path",
            "nir_path",
        },
        "gallery.json scene entry",
    )


def validate_public_dataset(*, strict: bool = False, require_atlas: bool = False) -> None:
    manifest = _read_json(WEB_DATA / "dataset-manifest.json")
    validate_dataset_manifest(manifest, require_atlas=require_atlas)
    validate_spots_payload(_read_json(WEB_DATA / "spots.json"), strict=strict)
    validate_segments_high_payload(_read_json(WEB_DATA / "segments-high.json"), strict=strict)
    validate_gallery_payload(_read_json(WEB_DATA / "gallery.json"), strict=strict)

    if require_atlas:
        atlas_dir = WEB_DATA / "atlas"
        if not (atlas_dir / "sections.json").exists():
            raise ValueError("atlas/sections.json is required")
        if not (atlas_dir / "gallery.json").exists():
            raise ValueError("atlas/gallery.json is required")
