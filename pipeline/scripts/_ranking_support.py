from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

CONFIGS_DIR = Path(__file__).resolve().parents[1] / "configs"
DEFAULT_HIGH_TRUST_SOURCES = {
    "well-known",
    "public-stormrider",
    "public-surfline-stormrider",
    "public-nomadsurfers",
    "surfline",
}
DEFAULT_WATCHLIST_WITHIN_DISTANCE_M = 1200.0
WATCHLIST_PRIORITY_DISTANCE_M = 1200.0
WATCHLIST_COORDINATE_REVIEW_DISTANCE_M = 1800.0


def evidence_sparsity_penalty(confidence: int) -> float:
    """Penalty for segments that rank mostly on geometry without corroboration."""
    if confidence <= 1:
        return 12.0
    if confidence == 2:
        return 4.0
    return 0.0


def classify_watchlist_action(
    item: dict[str, Any],
    *,
    tracked_slugs: set[str] | None = None,
    high_trust_sources: set[str] | None = None,
) -> tuple[str, str]:
    """Classify broader public spots into actionable watchlist buckets."""
    tracked_slugs = tracked_slugs or set()
    high_trust_sources = high_trust_sources or DEFAULT_HIGH_TRUST_SOURCES

    slug = item.get("slug")
    score = float(item.get("best_segment_score", 0.0))
    local_score = item.get("best_score_within_distance")
    local_score_value = float(local_score) if local_score is not None else 0.0
    source = item.get("spot_source")
    has_config = item.get("config_point_lon") is not None
    best_distance = item.get("best_segment_distance_m")
    best_distance_value = float(best_distance) if best_distance is not None else None
    selected_anchor_source = item.get("selected_anchor_source")
    selected_anchor_name = (item.get("selected_anchor_name") or "").strip().lower()
    spot_name = (item.get("spot_name") or "").strip().lower()
    anchor_matches_named_spot = (
        selected_anchor_source != "config-break"
        or not selected_anchor_name
        or not spot_name
        or selected_anchor_name == spot_name
    )

    if slug in tracked_slugs:
        return "already_tracked", "Already part of the strict trusted regression set."
    if score <= 0.0:
        return "no_segment_support", "No ranked segment currently supports this named spot."
    if score < 50.0:
        return "low_signal_watch", "Current ranked support is too weak to prioritize."

    if source == "wannasurf":
        if score >= 70.0 and local_score is not None and local_score_value < 70.0:
            return (
                "research_candidate",
                "Strong broad support exists, but local alignment is weaker than the peak segment for this research-grade source.",
            )
        if score >= 60.0:
            return "research_candidate", "Strong enough to monitor, but still a research-grade public source."
        return "low_signal_watch", "Weak support from a research-grade public source."

    if source in high_trust_sources:
        if score < 60.0:
            return "secondary_watch", "Public source is credible, but the current score is not strong enough yet."
        if local_score is not None and local_score_value >= 60.0:
            if not anchor_matches_named_spot:
                return (
                    "research_candidate",
                    "Trusted public source has strong local support, but it currently aligns to a different break anchor in the config.",
                )
            return (
                "priority_regression_candidate",
                "Trusted public source has strong local ranked support within the default watchlist window.",
            )
        if local_score is not None and local_score_value >= 50.0:
            return (
                "research_candidate",
                "Trusted public source has some local support, but not enough for immediate regression promotion.",
            )
        if has_config and best_distance_value is not None:
            if best_distance_value > WATCHLIST_COORDINATE_REVIEW_DISTANCE_M:
                return (
                    "coordinate_review_candidate",
                    "Best ranked segment is too far from the configured spot anchor to promote safely.",
                )
            if best_distance_value > WATCHLIST_PRIORITY_DISTANCE_M:
                return (
                    "research_candidate",
                    "Support is promising, but local alignment is still too broad for immediate regression promotion.",
                )
        return "priority_regression_candidate", "Strong score with credible local alignment from a trusted public source."

    return "secondary_watch", "Not yet strong enough or trusted enough to promote."


def validate_ranking_regressions(
    segments_by_id: dict[str, dict[str, Any]],
    regression_path: Path,
) -> tuple[bool, list[str]]:
    """Validate hand-picked ranking expectations against current output."""
    if not regression_path.exists():
        return True, []

    payload = json.loads(regression_path.read_text())
    issues: list[str] = []

    for case in payload.get("cases", []):
        name = case.get("name", "unnamed-case")

        segment_id = case.get("segment_id")
        if segment_id:
            segment = segments_by_id.get(segment_id)
            if segment is None:
                issues.append(f"{name}: missing segment {segment_id}")
                continue

            score = float(segment.get("composite_score", 0.0))
            min_score = case.get("min_score")
            max_score = case.get("max_score")
            if min_score is not None and score < float(min_score):
                issues.append(f"{name}: score {score:.1f} < min_score {float(min_score):.1f}")
            if max_score is not None and score > float(max_score):
                issues.append(f"{name}: score {score:.1f} > max_score {float(max_score):.1f}")
            continue

        higher_id = case.get("higher_segment_id")
        lower_id = case.get("lower_segment_id")
        if not higher_id or not lower_id:
            issues.append(f"{name}: missing comparison ids")
            continue

        higher = segments_by_id.get(higher_id)
        lower = segments_by_id.get(lower_id)
        if higher is None or lower is None:
            issues.append(f"{name}: missing segment in comparison")
            continue

        higher_score = float(higher.get("composite_score", 0.0))
        lower_score = float(lower.get("composite_score", 0.0))
        min_margin = float(case.get("min_margin", 0.0))

        if higher_score - lower_score < min_margin:
            issues.append(
                f"{name}: margin {higher_score - lower_score:.1f} < required {min_margin:.1f}"
            )

    return len(issues) == 0, issues


def _feature_centroid(feature: dict[str, Any]) -> tuple[float, float] | None:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") != "LineString":
        return None

    coords = geometry.get("coordinates") or []
    if not coords:
        return None

    xs = [float(coord[0]) for coord in coords]
    ys = [float(coord[1]) for coord in coords]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * radius_m * math.asin(math.sqrt(a))


def _threshold_issues(
    label: str,
    *,
    total_count: int,
    best_score: float,
    best_score_within_distance: float | None,
    count_ge_50: int,
    count_ge_60: int,
    count_ge_70: int,
    case: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    min_total = case.get("min_total_count")
    min_best_score = case.get("min_best_score")
    max_best_score = case.get("max_best_score")
    min_ge_50 = case.get("min_count_ge_50")
    max_ge_50 = case.get("max_count_ge_50")
    min_ge_60 = case.get("min_count_ge_60")
    max_ge_60 = case.get("max_count_ge_60")
    min_ge_70 = case.get("min_count_ge_70")
    max_ge_70 = case.get("max_count_ge_70")
    min_best_score_within_distance = case.get("min_best_score_within_distance")

    if min_total is not None and total_count < int(min_total):
        issues.append(f"{label}: total {total_count} < min_total_count {int(min_total)}")
    if min_best_score is not None and best_score < float(min_best_score):
        issues.append(f"{label}: best_score {best_score:.1f} < min_best_score {float(min_best_score):.1f}")
    if max_best_score is not None and best_score > float(max_best_score):
        issues.append(f"{label}: best_score {best_score:.1f} > max_best_score {float(max_best_score):.1f}")
    if min_ge_50 is not None and count_ge_50 < int(min_ge_50):
        issues.append(f"{label}: >=50 count {count_ge_50} < min_count_ge_50 {int(min_ge_50)}")
    if max_ge_50 is not None and count_ge_50 > int(max_ge_50):
        issues.append(f"{label}: >=50 count {count_ge_50} > max_count_ge_50 {int(max_ge_50)}")
    if min_ge_60 is not None and count_ge_60 < int(min_ge_60):
        issues.append(f"{label}: >=60 count {count_ge_60} < min_count_ge_60 {int(min_ge_60)}")
    if max_ge_60 is not None and count_ge_60 > int(max_ge_60):
        issues.append(f"{label}: >=60 count {count_ge_60} > max_count_ge_60 {int(max_ge_60)}")
    if min_ge_70 is not None and count_ge_70 < int(min_ge_70):
        issues.append(f"{label}: >=70 count {count_ge_70} < min_count_ge_70 {int(min_ge_70)}")
    if max_ge_70 is not None and count_ge_70 > int(max_ge_70):
        issues.append(f"{label}: >=70 count {count_ge_70} > max_count_ge_70 {int(max_ge_70)}")
    if min_best_score_within_distance is not None:
        observed = best_score_within_distance if best_score_within_distance is not None else 0.0
        if observed < float(min_best_score_within_distance):
            issues.append(
                f"{label}: best_score_within_distance {observed:.1f} < "
                f"min_best_score_within_distance {float(min_best_score_within_distance):.1f}"
            )
    return issues


def evaluate_spot_neighborhood(
    features: list[dict[str, Any]],
    *,
    lon: float,
    lat: float,
    radius_m: float,
    within_distance_m: float | None = None,
) -> dict[str, Any]:
    """Collect ranked segment stats around a spot center."""
    candidates: list[dict[str, Any]] = []

    for feature in features:
        centroid = _feature_centroid(feature)
        if centroid is None:
            continue

        cx, cy = centroid
        distance_m = haversine_m(lon, lat, cx, cy)
        if distance_m > radius_m:
            continue

        props = feature.get("properties") or {}
        candidates.append(
            {
                "segment_id": props.get("segment_id"),
                "score": float(props.get("composite_score", 0.0)),
                "orientation_deg": props.get("orientation_deg"),
                "distance_m": round(distance_m, 1),
                "confidence": props.get("confidence"),
                "evidence_sparsity_penalty": props.get("evidence_sparsity_penalty"),
                "false_positive_penalty": props.get("false_positive_penalty"),
                "coastal_context_penalty": props.get("coastal_context_penalty"),
                "geometry_component": props.get("geometry_component"),
                "foam_component": props.get("foam_component"),
                "profile_component": props.get("profile_component"),
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    best = candidates[0] if candidates else None
    scores = [candidate["score"] for candidate in candidates]
    nearby_focus = [
        candidate for candidate in candidates
        if within_distance_m is not None and candidate["distance_m"] <= within_distance_m
    ]
    best_focus = nearby_focus[0] if nearby_focus else None

    return {
        "radius_m": radius_m,
        "within_distance_m": within_distance_m,
        "nearby_segment_count": len(candidates),
        "best_segment_id": best["segment_id"] if best else None,
        "best_segment_score": best["score"] if best else 0.0,
        "best_segment_distance_m": best["distance_m"] if best else None,
        "best_segment_orientation_deg": best["orientation_deg"] if best else None,
        "best_segment_confidence": best["confidence"] if best else None,
        "best_segment_evidence_sparsity_penalty": (
            best["evidence_sparsity_penalty"] if best else None
        ),
        "best_segment_false_positive_penalty": best["false_positive_penalty"] if best else None,
        "best_segment_coastal_context_penalty": best["coastal_context_penalty"] if best else None,
        "best_segment_geometry_component": best["geometry_component"] if best else None,
        "best_segment_foam_component": best["foam_component"] if best else None,
        "best_segment_profile_component": best["profile_component"] if best else None,
        "best_segment_within_distance_id": best_focus["segment_id"] if best_focus else None,
        "best_score_within_distance": best_focus["score"] if best_focus else None,
        "best_segment_within_distance_m": best_focus["distance_m"] if best_focus else None,
        "count_ge_50": sum(score >= 50.0 for score in scores),
        "count_ge_60": sum(score >= 60.0 for score in scores),
        "count_ge_70": sum(score >= 70.0 for score in scores),
        "top_segments": candidates[:5],
    }


def _anchor_sort_key(result: dict[str, Any]) -> tuple[float, float]:
    local_score = result.get("best_score_within_distance")
    local_value = float(local_score) if local_score is not None else -1.0
    best_value = float(result.get("best_segment_score", 0.0))
    return (local_value, best_value)


def build_spot_neighborhood_report(
    features: list[dict[str, Any]],
    spots_payload: dict[str, Any],
    regression_payload: dict[str, Any] | None = None,
    *,
    default_within_distance_m: float | None = None,
) -> dict[str, Any]:
    """Build a spot-neighborhood calibration report from current ranked output."""
    cases_by_slug: dict[str, dict[str, Any]] = {}
    config_points: dict[str, tuple[float, float]] = {}
    if regression_payload:
        for case in regression_payload.get("spots", []):
            slug = case.get("slug")
            if slug:
                cases_by_slug[slug] = case
    for path in CONFIGS_DIR.glob("*.json"):
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        slug = payload.get("slug")
        point = payload.get("point")
        if slug and point and "lon" in point and "lat" in point:
            config_points[slug] = (float(point["lon"]), float(point["lat"]))

    neighborhoods: list[dict[str, Any]] = []
    follow_up_items: list[dict[str, Any]] = []
    for feature in spots_payload.get("features", []):
        props = feature.get("properties", {})
        if props.get("source") == "graham-local-knowledge":
            continue

        slug = props.get("slug")
        if not slug:
            continue

        lon, lat = feature.get("geometry", {}).get("coordinates", [None, None])
        if lon is None or lat is None:
            continue

        case = cases_by_slug.get(slug, {})
        config_point = config_points.get(slug)
        point_to_config_distance_m = (
            haversine_m(float(lon), float(lat), config_point[0], config_point[1])
            if config_point is not None
            else None
        )
        config_path = CONFIGS_DIR / f"{slug}.json"
        anchor_specs: list[dict[str, Any]] = [
            {"name": "spot-center", "lon": float(lon), "lat": float(lat), "source": "spot"}
        ]
        if config_path.exists():
            try:
                config_payload = json.loads(config_path.read_text())
            except json.JSONDecodeError:
                config_payload = {}
            for idx, br in enumerate(config_payload.get("breaks", [])):
                if "lon" in br and "lat" in br:
                    anchor_specs.append(
                        {
                            "name": br.get("name", f"break-{idx + 1}"),
                            "lon": float(br["lon"]),
                            "lat": float(br["lat"]),
                            "source": "config-break",
                        }
                    )
        radius_m = float(case.get("radius_m", 2500.0))
        within_distance_m = (
            float(case["within_distance_m"])
            if case.get("within_distance_m") is not None
            else (
                float(default_within_distance_m)
                if default_within_distance_m is not None
                else None
            )
        )
        anchor_results: list[dict[str, Any]] = []
        for anchor in anchor_specs:
            evaluated = evaluate_spot_neighborhood(
                features,
                lon=anchor["lon"],
                lat=anchor["lat"],
                radius_m=radius_m,
                within_distance_m=within_distance_m,
            )
            anchor_results.append(
                {
                    "anchor_name": anchor["name"],
                    "anchor_source": anchor["source"],
                    "anchor_lon": anchor["lon"],
                    "anchor_lat": anchor["lat"],
                    **evaluated,
                }
            )
        neighborhood = max(anchor_results, key=_anchor_sort_key)
        issues = _threshold_issues(
            slug,
            total_count=neighborhood["nearby_segment_count"],
            best_score=float(neighborhood["best_segment_score"]),
            best_score_within_distance=(
                float(neighborhood["best_score_within_distance"])
                if neighborhood["best_score_within_distance"] is not None
                else None
            ),
            count_ge_50=int(neighborhood["count_ge_50"]),
            count_ge_60=int(neighborhood["count_ge_60"]),
            count_ge_70=int(neighborhood["count_ge_70"]),
            case=case,
        )
        tracked = bool(case)
        meets_expectations = len(issues) == 0 if tracked else None
        has_local_requirement = case.get("within_distance_m") is not None
        local_support = neighborhood["best_score_within_distance"] is not None
        if not tracked:
            follow_up_action = "untracked"
            follow_up_reason = "Spot is currently informational and does not have a checked-in regression case."
        elif meets_expectations and (not has_local_requirement or local_support):
            follow_up_action = "none"
            if has_local_requirement:
                follow_up_reason = "Local spot support is present within the tracked distance window."
            else:
                follow_up_reason = "The tracked neighborhood currently meets expectations."
        elif meets_expectations and has_local_requirement and not local_support:
            if point_to_config_distance_m is not None and point_to_config_distance_m <= 250.0:
                follow_up_action = "spot_definition_review"
                follow_up_reason = (
                    "Spot coordinates align with the pipeline config, but no strong segment is present in the "
                    "local distance window."
                )
            else:
                follow_up_action = "coordinate_or_source_review"
                follow_up_reason = (
                    "Broad neighborhood support exists, but no strong segment is present in the local distance window."
                )
        else:
            local_only_issues = [
                issue for issue in issues
                if "best_score_within_distance" in issue
            ]
            broad_issues = [issue for issue in issues if issue not in local_only_issues]
            best_confidence = neighborhood.get("best_segment_confidence")
            evidence_penalty = float(neighborhood.get("best_segment_evidence_sparsity_penalty") or 0.0)
            false_positive_penalty = float(neighborhood.get("best_segment_false_positive_penalty") or 0.0)
            profile_component = float(neighborhood.get("best_segment_profile_component") or 0.0)
            foam_component = float(neighborhood.get("best_segment_foam_component") or 0.0)
            nearby_best = (
                neighborhood.get("best_segment_distance_m") is not None
                and float(neighborhood["best_segment_distance_m"]) <= 1000.0
            )
            if local_only_issues and not broad_issues:
                follow_up_action = "coordinate_or_source_review"
                follow_up_reason = "The broader neighborhood passes, but the local-distance support is weak or missing."
            elif (
                point_to_config_distance_m is not None
                and point_to_config_distance_m <= 250.0
                and nearby_best
                and best_confidence is not None
                and int(best_confidence) == 2
                and foam_component > 0.0
                and profile_component <= 0.0
            ):
                follow_up_action = "ranking_review"
                follow_up_reason = (
                    "A plausible nearby segment exists with foam evidence, but no swell-profile coverage is "
                    "available yet for the local neighborhood."
                )
            elif (
                point_to_config_distance_m is not None
                and point_to_config_distance_m <= 250.0
                and nearby_best
                and best_confidence is not None
                and int(best_confidence) < 3
                and evidence_penalty > 0.0
            ):
                follow_up_action = "ranking_review"
                follow_up_reason = (
                    "A plausible nearby segment exists, but the ranked neighborhood is still capped by sparse "
                    "corroborating evidence."
                )
            elif (
                point_to_config_distance_m is not None
                and point_to_config_distance_m <= 250.0
                and nearby_best
                and false_positive_penalty > 0.0
            ):
                follow_up_action = "ranking_review"
                follow_up_reason = (
                    "A plausible nearby segment exists, but contamination penalties are suppressing the "
                    "ranked neighborhood."
                )
            else:
                follow_up_action = "ranking_review"
                follow_up_reason = "The ranked neighborhood itself is too weak to meet the current expectations."

        neighborhoods.append(
            {
                "spot_name": props.get("name", slug),
                "slug": slug,
                "spot_lat": lat,
                "spot_lon": lon,
                "spot_source": props.get("source"),
                "spot_swell_window": props.get("swell_window"),
                "config_point_lon": config_point[0] if config_point is not None else None,
                "config_point_lat": config_point[1] if config_point is not None else None,
                "point_to_config_distance_m": round(point_to_config_distance_m, 1)
                if point_to_config_distance_m is not None
                else None,
                "anchor_count": len(anchor_results),
                "tracked_by_regression": tracked,
                "expectations": case or None,
                "meets_expectations": meets_expectations,
                "follow_up_action": follow_up_action,
                "follow_up_reason": follow_up_reason,
                "issues": issues,
                "selected_anchor_name": neighborhood["anchor_name"],
                "selected_anchor_source": neighborhood["anchor_source"],
                "selected_anchor_lon": neighborhood["anchor_lon"],
                "selected_anchor_lat": neighborhood["anchor_lat"],
                "anchor_results": anchor_results,
                **neighborhood,
            }
        )
        if follow_up_action != "none":
            follow_up_items.append(
                {
                    "slug": slug,
                    "spot_name": props.get("name", slug),
                    "action": follow_up_action,
                    "reason": follow_up_reason,
                }
            )

    best_scores = [float(item["best_segment_score"]) for item in neighborhoods]
    tracked = [item for item in neighborhoods if item["tracked_by_regression"]]
    return {
        "summary": {
            "total_ranked_segments": len(features),
            "trusted_spot_count": len(neighborhoods),
            "tracked_spot_count": len(tracked),
            "spots_meeting_expectations": sum(1 for item in tracked if item["meets_expectations"]),
            "spots_failing_expectations": sum(1 for item in tracked if item["meets_expectations"] is False),
            "best_score_stats": {
                "mean": round(sum(best_scores) / len(best_scores), 1) if best_scores else None,
                "median": round(sorted(best_scores)[len(best_scores) // 2], 1) if best_scores else None,
                "max": round(max(best_scores), 1) if best_scores else None,
                "min": round(min(best_scores), 1) if best_scores else None,
            },
            "follow_up_counts": {
                "coordinate_or_source_review": sum(
                    1 for item in follow_up_items if item["action"] == "coordinate_or_source_review"
                ),
                "spot_definition_review": sum(
                    1 for item in follow_up_items if item["action"] == "spot_definition_review"
                ),
                "ranking_review": sum(
                    1 for item in follow_up_items if item["action"] == "ranking_review"
                ),
                "untracked": sum(
                    1 for item in follow_up_items if item["action"] == "untracked"
                ),
            },
        },
        "spot_neighborhoods": neighborhoods,
        "follow_up_items": follow_up_items,
    }


def validate_ranking_region_regressions(
    features: list[dict[str, Any]],
    regression_path: Path,
) -> tuple[bool, list[str], list[str]]:
    """Validate region-level expectations against current ranked output."""
    if not regression_path.exists():
        return True, [], []

    payload = json.loads(regression_path.read_text())
    issues: list[str] = []
    summaries: list[str] = []

    for region in payload.get("regions", []):
        name = region.get("name", "unnamed-region")
        bbox = region.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            issues.append(f"{name}: invalid bbox")
            continue

        min_x, min_y, max_x, max_y = [float(value) for value in bbox]
        scores: list[float] = []
        top_segment_id: str | None = None
        top_segment_score = -1.0

        for feature in features:
            centroid = _feature_centroid(feature)
            if centroid is None:
                continue

            x, y = centroid
            if not (min_x <= x <= max_x and min_y <= y <= max_y):
                continue

            props = feature.get("properties") or {}
            score = float(props.get("composite_score", 0.0))
            scores.append(score)
            if score > top_segment_score:
                top_segment_score = score
                top_segment_id = props.get("segment_id")

        count = len(scores)
        max_score = max(scores) if scores else 0.0
        count_ge_50 = sum(score >= 50.0 for score in scores)
        count_ge_60 = sum(score >= 60.0 for score in scores)
        count_ge_70 = sum(score >= 70.0 for score in scores)

        summaries.append(
            f"  {name}: total={count}, max={max_score:.1f}, >=50={count_ge_50}, "
            f">=60={count_ge_60}, >=70={count_ge_70}, top={top_segment_id or 'none'}"
        )

        min_total = region.get("min_total_count")
        max_total = region.get("max_total_count")
        min_score = region.get("min_score")
        max_allowed_score = region.get("max_score")
        min_ge_50 = region.get("min_count_ge_50")
        max_ge_50 = region.get("max_count_ge_50")
        min_ge_60 = region.get("min_count_ge_60")
        max_ge_60 = region.get("max_count_ge_60")
        min_ge_70 = region.get("min_count_ge_70")
        max_ge_70 = region.get("max_count_ge_70")

        if min_total is not None and count < int(min_total):
            issues.append(f"{name}: total {count} < min_total_count {int(min_total)}")
        if max_total is not None and count > int(max_total):
            issues.append(f"{name}: total {count} > max_total_count {int(max_total)}")
        if min_score is not None and max_score < float(min_score):
            issues.append(f"{name}: max_score {max_score:.1f} < min_score {float(min_score):.1f}")
        if max_allowed_score is not None and max_score > float(max_allowed_score):
            issues.append(f"{name}: max_score {max_score:.1f} > max_score {float(max_allowed_score):.1f}")
        if min_ge_50 is not None and count_ge_50 < int(min_ge_50):
            issues.append(f"{name}: >=50 count {count_ge_50} < min_count_ge_50 {int(min_ge_50)}")
        if max_ge_50 is not None and count_ge_50 > int(max_ge_50):
            issues.append(f"{name}: >=50 count {count_ge_50} > max_count_ge_50 {int(max_ge_50)}")
        if min_ge_60 is not None and count_ge_60 < int(min_ge_60):
            issues.append(f"{name}: >=60 count {count_ge_60} < min_count_ge_60 {int(min_ge_60)}")
        if max_ge_60 is not None and count_ge_60 > int(max_ge_60):
            issues.append(f"{name}: >=60 count {count_ge_60} > max_count_ge_60 {int(max_ge_60)}")
        if min_ge_70 is not None and count_ge_70 < int(min_ge_70):
            issues.append(f"{name}: >=70 count {count_ge_70} < min_count_ge_70 {int(min_ge_70)}")
        if max_ge_70 is not None and count_ge_70 > int(max_ge_70):
            issues.append(f"{name}: >=70 count {count_ge_70} > max_count_ge_70 {int(max_ge_70)}")

    return len(issues) == 0, issues, summaries


def validate_spot_neighborhood_regressions(
    features: list[dict[str, Any]],
    spots_path: Path,
    regression_path: Path,
) -> tuple[bool, list[str], list[str]]:
    """Validate trusted named spots against nearby ranked segment neighborhoods."""
    if not spots_path.exists() or not regression_path.exists():
        return True, [], []

    spots_payload = json.loads(spots_path.read_text())
    payload = json.loads(regression_path.read_text())
    report = build_spot_neighborhood_report(features, spots_payload, payload)
    issues = [
        issue
        for item in report.get("spot_neighborhoods", [])
        for issue in item.get("issues", [])
    ]
    summaries: list[str] = []
    for item in report.get("spot_neighborhoods", []):
        top_segment_id = item.get("best_segment_id") or "none"
        best_distance_m = item.get("best_segment_distance_m")
        distance_suffix = f"@{best_distance_m:.0f}m" if best_distance_m is not None else ""
        summaries.append(
            f"  {item['slug']}: radius={item['radius_m']:.0f}m, total={item['nearby_segment_count']}, "
            f"best={item['best_segment_score']:.1f}, >=50={item['count_ge_50']}, "
            f">=60={item['count_ge_60']}, >=70={item['count_ge_70']}, "
            f"top={top_segment_id}{distance_suffix}"
        )

    return len(issues) == 0, issues, summaries


COMPASS_BEARINGS = {
    "N": 0.0,
    "NE": 45.0,
    "E": 90.0,
    "SE": 135.0,
    "S": 180.0,
    "SW": 225.0,
    "W": 270.0,
    "NW": 315.0,
}


def angular_difference(a: float, b: float) -> float:
    return abs(((a - b + 180.0) % 360.0) - 180.0)


def trusted_calibration_match(
    distance_m: float | None,
    spot_facing: str | None,
    segment_orientation_deg: float | None,
) -> bool:
    if distance_m is None or distance_m > 2500.0:
        return False
    if not spot_facing or segment_orientation_deg is None:
        return True

    expected = COMPASS_BEARINGS.get(str(spot_facing).upper())
    if expected is None:
        return True
    return angular_difference(expected, float(segment_orientation_deg)) <= 95.0
