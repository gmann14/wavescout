#!/usr/bin/env python3
"""Helpers for public web dataset manifests and contract validation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE_DATA = ROOT / "pipeline" / "data"
MANIFESTS = PIPELINE_DATA / "manifests"
WEB_DATA = ROOT / "web" / "public" / "data"
WEB_PUBLIC = ROOT / "web" / "public"

SUPPORTED_STATUSES = {"draft", "promoted", "retired"}
CONFIDENCE_LABELS = {"none", "low", "moderate", "high"}
VERIFICATION_STATUSES = {"confirmed", "candidate", "rejected"}
PUBLICATION_STATUSES = {"public_named", "public_coarse", "internal_only"}
BREAK_TYPES = {"beach", "point", "reef", "slab", "mixed", "unknown"}

IMAGE_DELIVERY_MODES = {"static-public", "cdn"}
GALLERY_URL_PREFIX_ENV = "WAVESCOUT_GALLERY_URL_PREFIX"
GALLERY_COLLECTION_SEGMENTS = ("gallery", "atlas-gallery")


def normalize_gallery_url_prefix(prefix: str | None) -> str | None:
    """Validate and normalize an optional CDN prefix.

    Returns ``None`` when no prefix is configured. Raises ``ValueError``
    for unsupported schemes (only absolute ``https://`` URLs are
    accepted). Trailing slashes are stripped so callers can join the
    prefix with web-root-relative paths without worrying about double
    slashes.
    """
    if prefix is None:
        return None
    prefix = prefix.strip()
    if not prefix:
        return None
    if prefix.startswith("//"):
        raise ValueError(
            "gallery URL prefix must be an absolute https URL, "
            f"not protocol-relative: {prefix!r}"
        )
    if not prefix.startswith("https://"):
        raise ValueError(
            "gallery URL prefix must use https://, "
            f"got: {prefix!r}"
        )
    return prefix.rstrip("/")


def gallery_url_prefix_from_env(env: dict[str, str] | None = None) -> str | None:
    """Read and normalize the CDN prefix from the process environment."""
    source = env if env is not None else os.environ
    return normalize_gallery_url_prefix(source.get(GALLERY_URL_PREFIX_ENV))


def _first_path_segment(path: str) -> tuple[str, str]:
    rest = path.lstrip("/")
    first, _, suffix = rest.partition("/")
    return first, suffix


def _prefix_collection_segment(prefix: str) -> str | None:
    parsed = urlparse(prefix)
    segment = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    if segment in GALLERY_COLLECTION_SEGMENTS:
        return segment
    return None


def _replace_prefix_collection(prefix: str, collection: str) -> str:
    current = _prefix_collection_segment(prefix)
    if current is None:
        return f"{prefix}/{collection}"
    return f"{prefix[: -(len(current) + 1)]}/{collection}"


def allowed_cdn_url_prefixes(prefix: str) -> tuple[str, ...]:
    """Return CDN URL prefixes allowed by a configured gallery prefix.

    A single env var drives both gallery collections. If the configured
    prefix ends in one known collection segment, the sibling collection
    is allowed at the same parent path.
    """
    normalized = normalize_gallery_url_prefix(prefix)
    if normalized is None:
        raise ValueError("CDN image delivery requires a gallery URL prefix")
    collection = _prefix_collection_segment(normalized)
    if collection is None:
        return tuple(
            f"{normalized}/{segment}" for segment in GALLERY_COLLECTION_SEGMENTS
        )
    return tuple(
        _replace_prefix_collection(normalized, segment)
        for segment in GALLERY_COLLECTION_SEGMENTS
    )


def normalize_image_delivery(image_delivery: dict[str, Any] | None) -> dict[str, Any]:
    """Validate and normalize dataset image-delivery metadata."""
    if image_delivery is None:
        return {"mode": "static-public", "gallery_url_prefix": None}
    mode = image_delivery.get("mode", "static-public")
    if mode not in IMAGE_DELIVERY_MODES:
        raise ValueError(
            f"image_delivery.mode must be one of {sorted(IMAGE_DELIVERY_MODES)}, got {mode!r}"
        )
    prefix = image_delivery.get("gallery_url_prefix")
    if mode == "static-public":
        if prefix not in (None, ""):
            raise ValueError("static-public image delivery must not set gallery_url_prefix")
        return {"mode": "static-public", "gallery_url_prefix": None}
    normalized_prefix = normalize_gallery_url_prefix(prefix)
    if normalized_prefix is None:
        raise ValueError("cdn image delivery requires gallery_url_prefix")
    return {"mode": "cdn", "gallery_url_prefix": normalized_prefix}


def public_gallery_url(path: str | None, *, prefix: str | None) -> str | None:
    """Return the public URL for a gallery image path.

    With no prefix, the existing web-root-relative path is returned
    unchanged. With a prefix, the path is joined onto the prefix. If
    the prefix already ends with the path's leading directory (for
    example, prefix ``https://cdn/gallery`` with path
    ``/gallery/foo/x.png``), the duplicate segment is collapsed so
    the resulting URL contains the directory exactly once.
    """
    if path is None:
        return None
    if prefix is None:
        return path
    if not path.startswith("/"):
        raise ValueError(
            "public_gallery_url expects a web-root-relative path "
            f"starting with '/': {path!r}"
        )
    normalized_prefix = normalize_gallery_url_prefix(prefix)
    assert normalized_prefix is not None  # for type checker

    first_segment, suffix = _first_path_segment(path)
    if first_segment in GALLERY_COLLECTION_SEGMENTS:
        collection_prefix = _replace_prefix_collection(normalized_prefix, first_segment)
        return f"{collection_prefix}/{suffix}" if suffix else collection_prefix

    rest = path.lstrip("/")
    return f"{normalized_prefix}/{rest}"


def image_delivery_metadata(*, prefix: str | None) -> dict[str, Any]:
    """Describe the image delivery mode for the dataset manifest."""
    normalized = normalize_gallery_url_prefix(prefix)
    if normalized is None:
        return {"mode": "static-public", "gallery_url_prefix": None}
    return {"mode": "cdn", "gallery_url_prefix": normalized}


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
    # Named spots in the canonical inventory are reference entries, not candidate
    # segments. Evidence confidence should affect evidence labeling, not whether
    # the known spot itself is treated as confirmed.
    if source == "graham-local-knowledge":
        return "confirmed"
    return "confirmed"


def map_display_eligible_for_segment(
    evidence_confidence_level: int | None,
    publication_status: str | None,
    orientation_deg: float | None = None,
    exposure_arc_deg: float | None = None,
    farfield_open_water_deg: float | None = None,
    nearfield_open_water_deg: float | None = None,
) -> bool:
    """Return whether a candidate segment is eligible for the main Map surface.

    This gate is intentionally conservative: only coarse-public candidates with at
    least moderate evidence, a primary swell-facing orientation, and substantial
    open-ocean exposure may appear on the main Map. Atlas can remain broader.
    """
    if publication_status != "public_coarse":
        return False
    if evidence_confidence_level is None:
        return False
    if evidence_confidence_level < 2:
        return False
    if orientation_deg is None or not (120.0 <= orientation_deg <= 220.0):
        return False
    if exposure_arc_deg is None or exposure_arc_deg < 90.0:
        return False
    if farfield_open_water_deg is None or farfield_open_water_deg < 90.0:
        return False
    if (
        nearfield_open_water_deg is not None
        and farfield_open_water_deg is not None
        and nearfield_open_water_deg - farfield_open_water_deg >= 35.0
    ):
        return False
    return True


def build_dataset_manifest(*, gallery_url_prefix: str | None = None) -> dict[str, Any]:
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
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_version": code_version,
        "config_version": "unknown",
        "source_manifests": _source_manifest_paths(),
        "artifacts": _artifact_paths(),
        "image_delivery": image_delivery_metadata(prefix=gallery_url_prefix),
    }


def write_dataset_manifest(*, gallery_url_prefix: str | None = None) -> Path:
    """Write the public dataset manifest.

    ``gallery_url_prefix`` defaults to ``None``, which preserves the
    historical static-hosted behavior. Builders that want to record a
    CDN delivery mode pass the normalized prefix explicitly.
    """
    if gallery_url_prefix is None:
        gallery_url_prefix = gallery_url_prefix_from_env()
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    manifest = build_dataset_manifest(gallery_url_prefix=gallery_url_prefix)
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
    if "image_delivery" in manifest:
        normalize_image_delivery(manifest["image_delivery"])
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
            "map_display_eligible",
            "surf_potential_score",
            "evidence_confidence_level",
            "evidence_confidence_label",
            "quality_status",
            "coastal_exposure_class",
            "coastal_context_penalty",
            "evidence_sparsity_penalty",
            "nearfield_open_water_deg",
            "nearfield_blocked_ratio",
            "farfield_open_water_deg",
            "farfield_blocked_ratio",
            "score_components",
            "foam_obs_count",
            "turn_on_threshold_m",
            "optimal_swell_range",
            "primary_direction",
            "explanation",
        },
        "segments-high.json feature.properties",
    )
    if "confidence" in props:
        raise ValueError("segments-high.json must not expose legacy confidence in strict mode")
    for feature in features:
        props = feature.get("properties", {})
        if props.get("publication_status") != "public_coarse":
            continue
        coords = ((feature.get("geometry") or {}).get("coordinates")) or []
        if len(coords) != 2:
            raise ValueError("segments-high.json public_coarse features must be point coordinates")
        if any(round(coord, 3) != coord for coord in coords):
            raise ValueError("segments-high.json public_coarse coordinates must be rounded to 3 decimals max")


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


def _public_asset_path(public_root: Path, web_path: str, *, label: str) -> Path:
    if not web_path.startswith("/"):
        raise ValueError(f"{label} image path must be web-root-relative: {web_path}")

    public_root = public_root.resolve()
    candidate = (public_root / web_path.lstrip("/")).resolve()
    try:
        candidate.relative_to(public_root)
    except ValueError as exc:
        raise ValueError(f"{label} image path escapes web/public: {web_path}") from exc
    return candidate


def _classify_image_path(web_path: str, *, label: str, slug: str, date: str, key: str) -> str:
    """Classify a non-null image path as 'local', 'remote-https', or raise."""
    if web_path.startswith("//"):
        raise ValueError(
            f"{label} {slug}:{date} {key} protocol-relative URLs are not allowed: {web_path}"
        )
    if web_path.startswith("https://"):
        return "remote-https"
    if web_path.startswith("/"):
        return "local"
    raise ValueError(
        f"{label} {slug}:{date} {key} has unsupported scheme or shape: {web_path}"
    )


def validate_gallery_asset_paths(
    payload: dict[str, Any],
    *,
    public_root: Path = WEB_PUBLIC,
    label: str = "gallery.json",
    image_delivery: dict[str, Any] | None = None,
) -> None:
    """Validate that every non-null gallery image path is reachable.

    ``image_delivery`` describes how the manifest's images are served.
    When the mode is ``cdn``, ``https://`` URLs are allowed (and not
    fetched). Otherwise only web-root-relative paths under
    ``public_root`` are allowed.
    """
    image_keys = ("rgb_path", "nir_path", "annotated_rgb_path", "annotated_nir_path")
    entries = payload.get("spots") or payload.get("sections") or []

    delivery = normalize_image_delivery(image_delivery)
    delivery_mode = delivery["mode"]
    allowed_remote_prefixes = (
        allowed_cdn_url_prefixes(delivery["gallery_url_prefix"])
        if delivery_mode == "cdn"
        else ()
    )

    missing: list[str] = []
    remote_count = 0
    for entry in entries:
        slug = entry.get("slug") or entry.get("section_id") or "unknown"
        for scene in entry.get("scenes", []):
            date = scene.get("date", "unknown-date")
            for key in image_keys:
                web_path = scene.get(key)
                if not web_path:
                    continue
                if not isinstance(web_path, str):
                    raise ValueError(f"{label} {slug}:{date} {key} must be a string or null")
                kind = _classify_image_path(
                    web_path, label=label, slug=slug, date=date, key=key
                )
                if kind == "remote-https":
                    if delivery_mode != "cdn":
                        raise ValueError(
                            f"{label} {slug}:{date} {key} uses https URL but "
                            "dataset image_delivery.mode is not 'cdn': "
                            f"{web_path}"
                        )
                    if not any(
                        web_path == prefix or web_path.startswith(f"{prefix}/")
                        for prefix in allowed_remote_prefixes
                    ):
                        raise ValueError(
                            f"{label} {slug}:{date} {key} is outside configured "
                            f"gallery_url_prefix {delivery['gallery_url_prefix']!r}: {web_path}"
                        )
                    remote_count += 1
                    continue
                asset_path = _public_asset_path(public_root, web_path, label=label)
                if not asset_path.is_file():
                    missing.append(f"{slug}:{date} {key} -> {web_path}")

    if missing:
        sample = "; ".join(missing[:10])
        suffix = f" (+{len(missing) - 10} more)" if len(missing) > 10 else ""
        raise ValueError(f"{label} references missing public image assets: {sample}{suffix}")


def validate_public_dataset(*, strict: bool = False, require_atlas: bool = False) -> None:
    manifest = _read_json(WEB_DATA / "dataset-manifest.json")
    validate_dataset_manifest(manifest, require_atlas=require_atlas)
    image_delivery = manifest.get("image_delivery")
    validate_spots_payload(_read_json(WEB_DATA / "spots.json"), strict=strict)
    validate_segments_high_payload(_read_json(WEB_DATA / "segments-high.json"), strict=strict)
    gallery_payload = _read_json(WEB_DATA / "gallery.json")
    validate_gallery_payload(gallery_payload, strict=strict)
    validate_gallery_asset_paths(
        gallery_payload, label="gallery.json", image_delivery=image_delivery
    )

    if require_atlas:
        atlas_dir = WEB_DATA / "atlas"
        if not (atlas_dir / "sections.json").exists():
            raise ValueError("atlas/sections.json is required")
        if not (atlas_dir / "gallery.json").exists():
            raise ValueError("atlas/gallery.json is required")
        validate_gallery_asset_paths(
            _read_json(atlas_dir / "gallery.json"),
            label="atlas/gallery.json",
            image_delivery=image_delivery,
        )
