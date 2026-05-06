from __future__ import annotations

import csv
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pipeline.research.swell_lines import CALIBRATION_PAIRS_PATH, load_calibration_pairs

VALID_REVIEW_LABELS = {"clear_positive", "ambiguous", "clear_negative"}
ROOT = Path(__file__).resolve().parents[3]

SCENE_FILTER_PROFILES = {
    "strict": {
        "max_cloud_pct": 10.0,
        "min_quality_score": 90.0,
        "min_swell_height_m": 1.5,
        "min_swell_period_s": 8.0,
        "max_additional_per_spot": 5,
    },
    "broad": {
        "max_cloud_pct": 15.0,
        "min_quality_score": 75.0,
        "min_swell_height_m": 1.0,
        "min_swell_period_s": 7.0,
        "max_additional_per_spot": 8,
    },
}

DEFAULT_GALLERY_MANIFEST_PATH = Path("pipeline/data/gallery/manifest.json")
DEFAULT_FOAM_MANIFESTS_DIR = Path("pipeline/data/manifests")
DEFAULT_GEE_PROJECT = "seotakeoff"
SCENE_DISCOVERY_MIN_DATE = "2021-10-01"
SCENE_DISCOVERY_MAX_CLOUD_PERCENT = 15.0
OVERPASS_HOUR_UTC = 15
OPENMETEO_DELAY_S = 0.12
MAX_RETRIES = 3
RETRY_DELAY_S = 10
IMAGE_WIDTH = 800
RGB_VIS = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000, "gamma": 1.3}
NIR_VIS = {"bands": ["B8", "B8", "B8"], "min": 0, "max": 2000, "gamma": 1.4}


def load_json(path: Path | str) -> dict:
    with Path(path).open() as handle:
        return json.load(handle)


def write_json(path: Path | str, payload: dict) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def repo_path(path: Path | str | None) -> str | None:
    if path is None:
        return None
    raw_value = str(path)
    if raw_value.startswith("/") and not Path(raw_value).exists():
        return raw_value
    value = Path(raw_value)
    if not value.is_absolute():
        return raw_value
    try:
        return str(value.resolve().relative_to(ROOT))
    except ValueError:
        return raw_value


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def selection_defaults(profile: str) -> dict[str, float | int]:
    try:
        defaults = SCENE_FILTER_PROFILES[profile]
    except KeyError as exc:
        raise ValueError(f"Unknown review profile: {profile}") from exc
    return dict(defaults)


def wave_energy(height_m: float | None, period_s: float | None) -> float | None:
    if height_m is None or period_s is None:
        return None
    import math

    return (1025 * 9.81**2 * height_m**2 * period_s) / (64 * math.pi)


def _gallery_scene_index(path: Path | str = DEFAULT_GALLERY_MANIFEST_PATH) -> dict[str, dict[str, dict]]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return {}
    payload = load_json(manifest_path)
    return {
        spot["slug"]: {scene["date"]: scene for scene in spot.get("scenes", [])}
        for spot in payload.get("spots", [])
    }


def _config_payload(config_path: Path | str) -> dict:
    return load_json(config_path)


def _scene_quality_index(foam_manifest: dict) -> dict[str, dict]:
    return {row["date"]: row for row in foam_manifest.get("scene_quality", [])}


def _foam_detection_scene_index(foam_manifest: dict) -> dict[str, dict]:
    by_date: dict[str, dict] = {}
    for detection in foam_manifest.get("detections", []):
        by_date.setdefault(detection["date"], detection)
    return by_date


def _bbox_center(bbox: list[float]) -> tuple[float, float]:
    return ((bbox[1] + bbox[3]) / 2.0, (bbox[0] + bbox[2]) / 2.0)


def _scene_record(
    *,
    pair: dict,
    scene: dict,
    scene_source: str,
    gallery_scene: dict | None,
) -> dict:
    energy = scene.get("wave_energy")
    if energy is None:
        energy = wave_energy(scene.get("swell_height_m"), scene.get("swell_period_s"))
    return {
        "scene_id": f"{pair['slug']}_{scene['date']}",
        "spot_slug": pair["slug"],
        "spot_name": pair["spot_name"],
        "config_path": pair.get("config_path") or f"pipeline/configs/{pair['slug']}.json",
        "bbox": pair.get("bbox"),
        "window_bbox": pair.get("window_bbox"),
        "date": scene["date"],
        "scene_source": scene_source,
        "swell_height_m": scene.get("swell_height_m"),
        "swell_period_s": scene.get("swell_period_s"),
        "swell_direction_deg": scene.get("swell_direction_deg"),
        "cloud_pct": scene.get("cloud_pct"),
        "quality_score": scene.get("quality_score"),
        "snow_land_pct": scene.get("snow_land_pct"),
        "valid_pct": scene.get("valid_pct"),
        "shadow_pct": scene.get("shadow_pct"),
        "wave_energy": energy,
        "bin_label": scene.get("bin_label"),
        "foam_fraction": scene.get("foam_fraction"),
        "rgb_path": (gallery_scene or {}).get("rgb_path"),
        "nir_path": (gallery_scene or {}).get("nir_path"),
        "annotated_rgb_path": (gallery_scene or {}).get("annotated_rgb_path"),
        "annotated_nir_path": (gallery_scene or {}).get("annotated_nir_path"),
        "publishable": (gallery_scene or {}).get("publishable"),
        "quality_status": (gallery_scene or {}).get("quality_status"),
    }


def _scene_meets_filters(
    scene: dict,
    *,
    max_cloud_pct: float,
    min_quality_score: float,
    min_swell_height_m: float,
    min_swell_period_s: float,
) -> bool:
    return (
        (scene.get("cloud_pct") or 999.0) <= max_cloud_pct
        and (scene.get("quality_score") or 0.0) >= min_quality_score
        and (scene.get("swell_height_m") or 0.0) >= min_swell_height_m
        and (scene.get("swell_period_s") or 0.0) >= min_swell_period_s
    )


def _candidate_sort_key(scene: dict) -> tuple[float, float, float, str]:
    return (
        -(scene.get("wave_energy") or -1.0),
        -(scene.get("quality_score") or 0.0),
        -(scene.get("swell_period_s") or 0.0),
        scene["date"],
    )


def _date_after(date_str: str) -> str:
    return (date.fromisoformat(date_str) + timedelta(days=1)).isoformat()


def _date_on_or_after(left: str, right: str) -> bool:
    return date.fromisoformat(left) >= date.fromisoformat(right)


def _init_gee(project: str | None = None) -> None:
    from pipeline.scripts._script_utils import init_gee as init_gee_helper

    init_gee_helper(project=project or DEFAULT_GEE_PROJECT)


def get_clear_scene_dates(
    *,
    bbox: list[float],
    start_date: str,
    end_date: str,
    max_cloud_percent: float = SCENE_DISCOVERY_MAX_CLOUD_PERCENT,
) -> list[str]:
    import ee

    end_exclusive = (date.fromisoformat(end_date) + timedelta(days=1)).isoformat()
    roi = ee.Geometry.Rectangle(bbox)
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start_date, end_exclusive)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_percent))
    )
    return (
        collection.aggregate_array("system:time_start")
        .map(lambda t: ee.Date(t).format("YYYY-MM-dd"))
        .distinct()
        .sort()
        .getInfo()
    )


def get_scl_quality(
    *,
    date_str: str,
    bbox: list[float],
    max_cloud_percent: float = SCENE_DISCOVERY_MAX_CLOUD_PERCENT,
) -> dict:
    import ee

    defaults = {
        "cloud_pct": None,
        "snow_land_pct": None,
        "valid_pct": None,
        "shadow_pct": None,
        "quality_score": None,
    }
    try:
        roi = ee.Geometry.Rectangle(bbox)
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(roi)
            .filterDate(date_str, ee.Date(date_str).advance(1, "day"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_percent))
            .sort("CLOUDY_PIXEL_PERCENTAGE")
        )
        if collection.size().getInfo() == 0:
            return defaults

        scl = collection.first().select("SCL")
        histogram = scl.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=roi,
            scale=10,
            maxPixels=1e8,
        ).getInfo()
        hist = histogram.get("SCL", {})
        if not hist:
            return defaults

        total = sum(hist.values())
        if total == 0:
            return defaults

        cloud_px = sum(hist.get(str(v), 0) for v in (8, 9, 10))
        shadow_px = hist.get("3", 0)
        snow_px = hist.get("11", 0)
        water_px = hist.get("6", 0)
        nodata_px = hist.get("0", 0)
        valid_px = total - nodata_px
        non_water_px = valid_px - water_px

        cloud_pct = (cloud_px / total) * 100
        valid_pct = (valid_px / total) * 100
        snow_land_pct = (snow_px / max(non_water_px, 1)) * 100
        shadow_pct = (shadow_px / total) * 100
        quality_score = (
            (1.0 - min(cloud_pct / 100.0, 1.0)) * 40.0
            + min(valid_pct / 100.0, 1.0) * 30.0
            + (1.0 - min(snow_land_pct / 100.0, 1.0)) * 20.0
            + (1.0 - min(shadow_pct / 100.0, 1.0)) * 10.0
        )
        return {
            "cloud_pct": round(cloud_pct, 2),
            "snow_land_pct": round(snow_land_pct, 2),
            "valid_pct": round(valid_pct, 2),
            "shadow_pct": round(shadow_pct, 2),
            "quality_score": round(quality_score, 1),
        }
    except Exception:
        return defaults


def get_conditions_batch(lat: float, lon: float, dates: list[str]) -> dict[str, dict]:
    import requests
    from collections import defaultdict

    if not dates:
        return {}

    results: dict[str, dict] = {}
    by_month: defaultdict[str, list[str]] = defaultdict(list)
    for scene_date in dates:
        by_month[scene_date[:7]].append(scene_date)

    for month_key in sorted(by_month.keys()):
        month_dates = by_month[month_key]
        start_date = min(month_dates)
        end_date = max(month_dates)
        try:
            resp = requests.get(
                "https://marine-api.open-meteo.com/v1/marine",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "start_date": start_date,
                    "end_date": end_date,
                    "hourly": "swell_wave_height,swell_wave_period,swell_wave_direction",
                },
                timeout=30,
            )
            resp.raise_for_status()
            hourly = resp.json().get("hourly", {})
            times = hourly.get("time", [])
            heights = hourly.get("swell_wave_height", [])
            periods = hourly.get("swell_wave_period", [])
            directions = hourly.get("swell_wave_direction", [])
            for index, timestamp in enumerate(times):
                date_str = timestamp[:10]
                hour = int(timestamp[11:13]) if len(timestamp) > 11 else 0
                if hour == OVERPASS_HOUR_UTC and date_str in month_dates:
                    results[date_str] = {
                        "swell_height_m": heights[index] if index < len(heights) else None,
                        "swell_period_s": periods[index] if index < len(periods) else None,
                        "swell_direction_deg": directions[index] if index < len(directions) else None,
                    }
        except Exception:
            pass
        time.sleep(OPENMETEO_DELAY_S)

    for scene_date in dates:
        results.setdefault(
            scene_date,
            {
                "swell_height_m": None,
                "swell_period_s": None,
                "swell_direction_deg": None,
            },
        )
    return results


def _gallery_enriched_scene(
    *,
    pair: dict,
    base_scene: dict,
    gallery_lookup: dict[str, dict[str, dict]],
    source: str,
) -> dict:
    gallery_scene = gallery_lookup.get(pair["slug"], {}).get(base_scene["date"])
    return _scene_record(
        pair=pair,
        scene=base_scene,
        scene_source=source,
        gallery_scene=gallery_scene,
    )


def _load_local_scene_catalog_for_pair(
    *,
    pair: dict,
    manifests_dir: Path | str,
    gallery_lookup: dict[str, dict[str, dict]],
) -> list[dict]:
    manifest_path = Path(manifests_dir) / f"{pair['slug']}_foam_detections.json"
    if not manifest_path.exists():
        return []

    foam_manifest = load_json(manifest_path)
    quality_by_date = _scene_quality_index(foam_manifest)
    scene_by_date = _foam_detection_scene_index(foam_manifest)
    scenes: list[dict] = []
    for scene_date in sorted(scene_by_date.keys()):
        detection = scene_by_date[scene_date]
        quality = quality_by_date.get(scene_date, {})
        scenes.append(
            _gallery_enriched_scene(
                pair=pair,
                base_scene={
                    "date": scene_date,
                    "swell_height_m": detection.get("swell_height_m"),
                    "swell_period_s": detection.get("swell_period_s"),
                    "swell_direction_deg": detection.get("swell_direction_deg"),
                    "cloud_pct": quality.get("cloud_pct", detection.get("cloud_pct")),
                    "quality_score": quality.get("quality_score", detection.get("quality_score")),
                    "snow_land_pct": quality.get("snow_land_pct", detection.get("snow_land_pct")),
                    "valid_pct": quality.get("valid_pct", detection.get("valid_pct")),
                    "shadow_pct": quality.get("shadow_pct", detection.get("shadow_pct")),
                    "wave_energy": wave_energy(detection.get("swell_height_m"), detection.get("swell_period_s")),
                    "bin_label": None,
                    "foam_fraction": detection.get("foam_fraction"),
                },
                gallery_lookup=gallery_lookup,
                source="foam_manifest",
            )
        )
    return scenes


def _refresh_scene_catalog_for_pair(
    *,
    pair: dict,
    gallery_lookup: dict[str, dict[str, dict]],
    start_date: str,
    end_date: str,
    max_cloud_percent: float,
) -> list[dict]:
    if _date_on_or_after(start_date, _date_after(end_date)):
        return []

    config = _config_payload(pair.get("config_path") or f"pipeline/configs/{pair['slug']}.json")
    bbox = pair.get("bbox") or config["bbox"]
    point = config.get("point") or {}
    lat = point.get("lat")
    lon = point.get("lon")
    if lat is None or lon is None:
        lat, lon = _bbox_center(bbox)

    clear_dates = get_clear_scene_dates(
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        max_cloud_percent=max_cloud_percent,
    )
    if not clear_dates:
        return []

    conditions = get_conditions_batch(lat, lon, clear_dates)
    scenes: list[dict] = []
    for scene_date in clear_dates:
        quality = get_scl_quality(
            date_str=scene_date,
            bbox=bbox,
            max_cloud_percent=max_cloud_percent,
        )
        condition = conditions.get(scene_date, {})
        scenes.append(
            _gallery_enriched_scene(
                pair=pair,
                base_scene={
                    "date": scene_date,
                    "swell_height_m": condition.get("swell_height_m"),
                    "swell_period_s": condition.get("swell_period_s"),
                    "swell_direction_deg": condition.get("swell_direction_deg"),
                    "cloud_pct": quality.get("cloud_pct"),
                    "quality_score": quality.get("quality_score"),
                    "snow_land_pct": quality.get("snow_land_pct"),
                    "valid_pct": quality.get("valid_pct"),
                    "shadow_pct": quality.get("shadow_pct"),
                    "wave_energy": wave_energy(condition.get("swell_height_m"), condition.get("swell_period_s")),
                    "bin_label": None,
                    "foam_fraction": None,
                },
                gallery_lookup=gallery_lookup,
                source="gee_refresh",
            )
        )
    return scenes


def build_scene_catalog(
    *,
    pairs_path: Path | str = CALIBRATION_PAIRS_PATH,
    manifests_dir: Path | str = DEFAULT_FOAM_MANIFESTS_DIR,
    gallery_manifest_path: Path | str = DEFAULT_GALLERY_MANIFEST_PATH,
    refresh_recent: bool = False,
    gee_project: str | None = None,
    refresh_end_date: str | None = None,
    max_cloud_percent: float = SCENE_DISCOVERY_MAX_CLOUD_PERCENT,
) -> dict:
    pairs = load_calibration_pairs(pairs_path)
    gallery_lookup = _gallery_scene_index(gallery_manifest_path)
    refresh_end_date = refresh_end_date or date.today().isoformat()
    if refresh_recent:
        _init_gee(project=gee_project)

    spots: list[dict] = []
    total_scene_count = 0
    total_refreshed_count = 0

    for pair in pairs:
        local_scenes = _load_local_scene_catalog_for_pair(
            pair=pair,
            manifests_dir=manifests_dir,
            gallery_lookup=gallery_lookup,
        )
        latest_local_date = max((scene["date"] for scene in local_scenes), default=None)
        refreshed_scenes: list[dict] = []
        if refresh_recent:
            refresh_start_date = _date_after(latest_local_date) if latest_local_date else SCENE_DISCOVERY_MIN_DATE
            if _date_on_or_after(refresh_end_date, refresh_start_date):
                refreshed_scenes = _refresh_scene_catalog_for_pair(
                    pair=pair,
                    gallery_lookup=gallery_lookup,
                    start_date=refresh_start_date,
                    end_date=refresh_end_date,
                    max_cloud_percent=max_cloud_percent,
                )

        merged_by_date = {scene["date"]: scene for scene in local_scenes}
        for scene in refreshed_scenes:
            merged_by_date.setdefault(scene["date"], scene)
        scenes = [merged_by_date[key] for key in sorted(merged_by_date.keys())]

        total_scene_count += len(scenes)
        total_refreshed_count += len(refreshed_scenes)
        spots.append(
            {
                "spot_slug": pair["slug"],
                "spot_name": pair["spot_name"],
                "config_path": pair.get("config_path") or f"pipeline/configs/{pair['slug']}.json",
                "local_scene_count": len(local_scenes),
                "refreshed_scene_count": len(refreshed_scenes),
                "latest_local_date": latest_local_date,
                "latest_scene_date": max((scene["date"] for scene in scenes), default=None),
                "scenes": scenes,
            }
        )

    return {
        "version": 2,
        "generated_at_utc": now_utc_iso(),
        "pairs_path": repo_path(pairs_path),
        "manifests_dir": repo_path(manifests_dir),
        "gallery_manifest_path": repo_path(gallery_manifest_path),
        "refresh_recent": refresh_recent,
        "refresh_end_date": refresh_end_date,
        "max_cloud_percent": max_cloud_percent,
        "gee_project": gee_project or DEFAULT_GEE_PROJECT if refresh_recent else None,
        "summary": {
            "spot_count": len(spots),
            "scene_count": total_scene_count,
            "refreshed_scene_count": total_refreshed_count,
        },
        "spots": spots,
    }


def _candidate_record(
    *,
    pair: dict,
    scene: dict,
    source: str,
    is_frozen_organized: bool,
    selection_rank_within_spot: int,
) -> dict:
    scene_id = f"{pair['slug']}_{scene['date']}"
    return {
        "review_id": scene_id,
        "scene_id": scene_id,
        "spot_slug": pair["slug"],
        "spot_name": pair["spot_name"],
        "date": scene["date"],
        "source": source,
        "scene_source": scene.get("scene_source"),
        "is_frozen_organized": is_frozen_organized,
        "selection_rank_within_spot": selection_rank_within_spot,
        "config_path": scene.get("config_path") or pair.get("config_path"),
        "bbox": scene.get("bbox") or pair.get("bbox"),
        "window_bbox": scene.get("window_bbox") or pair.get("window_bbox"),
        "swell_height_m": scene.get("swell_height_m"),
        "swell_period_s": scene.get("swell_period_s"),
        "swell_direction_deg": scene.get("swell_direction_deg"),
        "cloud_pct": scene.get("cloud_pct"),
        "quality_score": scene.get("quality_score"),
        "wave_energy": scene.get("wave_energy"),
        "bin_label": scene.get("bin_label"),
        "rgb_path": repo_path(scene.get("rgb_path")),
        "nir_path": repo_path(scene.get("nir_path")),
        "annotated_rgb_path": repo_path(scene.get("annotated_rgb_path")),
        "annotated_nir_path": repo_path(scene.get("annotated_nir_path")),
        "publishable": scene.get("publishable"),
        "quality_status": scene.get("quality_status"),
    }


def build_candidate_scenes(
    *,
    scene_catalog: dict,
    pairs_path: Path | str = CALIBRATION_PAIRS_PATH,
    profile: str = "strict",
    max_additional_per_spot: int | None = None,
    max_cloud_pct: float | None = None,
    min_quality_score: float | None = None,
    min_swell_height_m: float | None = None,
    min_swell_period_s: float | None = None,
) -> dict:
    defaults = selection_defaults(profile)
    max_additional_per_spot = (
        int(max_additional_per_spot)
        if max_additional_per_spot is not None
        else int(defaults["max_additional_per_spot"])
    )
    max_cloud_pct = float(max_cloud_pct) if max_cloud_pct is not None else float(defaults["max_cloud_pct"])
    min_quality_score = (
        float(min_quality_score) if min_quality_score is not None else float(defaults["min_quality_score"])
    )
    min_swell_height_m = (
        float(min_swell_height_m) if min_swell_height_m is not None else float(defaults["min_swell_height_m"])
    )
    min_swell_period_s = (
        float(min_swell_period_s) if min_swell_period_s is not None else float(defaults["min_swell_period_s"])
    )

    pairs = load_calibration_pairs(pairs_path)
    spot_lookup = {spot["spot_slug"]: spot for spot in scene_catalog.get("spots", [])}

    candidates: list[dict] = []
    per_spot: list[dict] = []

    for pair in pairs:
        catalog_spot = spot_lookup.get(pair["slug"], {})
        scene_lookup = {scene["date"]: scene for scene in catalog_spot.get("scenes", [])}
        frozen_scene = dict(pair["organized_scene"])
        catalog_frozen_scene = scene_lookup.get(frozen_scene["date"])
        if catalog_frozen_scene:
            frozen_scene = {**catalog_frozen_scene, **frozen_scene}

        candidates.append(
            _candidate_record(
                pair=pair,
                scene=frozen_scene,
                source="frozen_organized",
                is_frozen_organized=True,
                selection_rank_within_spot=0,
            )
        )

        additional_pool = [
            scene
            for scene in catalog_spot.get("scenes", [])
            if scene.get("date") != frozen_scene["date"]
            and _scene_meets_filters(
                scene,
                max_cloud_pct=max_cloud_pct,
                min_quality_score=min_quality_score,
                min_swell_height_m=min_swell_height_m,
                min_swell_period_s=min_swell_period_s,
            )
        ]
        additional_pool = sorted(additional_pool, key=_candidate_sort_key)
        selected_additional = additional_pool[:max_additional_per_spot]

        for index, scene in enumerate(selected_additional, start=1):
            candidates.append(
                _candidate_record(
                    pair=pair,
                    scene=scene,
                    source="development_candidate",
                    is_frozen_organized=False,
                    selection_rank_within_spot=index,
                )
            )

        per_spot.append(
            {
                "spot_slug": pair["slug"],
                "spot_name": pair["spot_name"],
                "frozen_date": frozen_scene["date"],
                "frozen_in_catalog": catalog_frozen_scene is not None,
                "selected_total": 1 + len(selected_additional),
                "additional_selected": len(selected_additional),
                "additional_target": max_additional_per_spot,
                "additional_shortfall": max_additional_per_spot - len(selected_additional),
                "qualifying_additional_pool_size": len(additional_pool),
            }
        )

    return {
        "version": 2,
        "generated_at_utc": now_utc_iso(),
        "pairs_path": repo_path(pairs_path),
        "scene_catalog_summary": scene_catalog.get("summary", {}),
        "profile": profile,
        "criteria": {
            "max_cloud_pct": max_cloud_pct,
            "min_quality_score": min_quality_score,
            "min_swell_height_m": min_swell_height_m,
            "min_swell_period_s": min_swell_period_s,
            "max_additional_per_spot": max_additional_per_spot,
        },
        "summary": {
            "spot_count": len(per_spot),
            "frozen_scene_count": len(per_spot),
            "selected_scene_count": len(candidates),
            "target_scene_count": len(per_spot) * (1 + max_additional_per_spot),
            "shortfall": len(per_spot) * (1 + max_additional_per_spot) - len(candidates),
        },
        "spots": per_spot,
        "candidates": candidates,
    }


def _fetch_thumbnail(url: str) -> bytes | None:
    import requests

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=120)
            if response.status_code == 200:
                return response.content
            if response.status_code == 429:
                time.sleep(RETRY_DELAY_S * (attempt + 1))
                continue
        except requests.RequestException:
            pass
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY_S)
    return None


def _find_scene_image(date_str: str, bbox: list[float]):
    import ee

    roi = ee.Geometry.Rectangle(bbox)
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(date_str, ee.Date(date_str).advance(1, "day"))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    if collection.size().getInfo() == 0:
        return None
    return ee.Image(collection.first())


def ensure_candidate_review_images(
    candidates_payload: dict,
    *,
    review_images_dir: Path | str,
    gee_project: str | None = None,
    force: bool = False,
) -> dict:
    _init_gee(project=gee_project)
    output_root = Path(review_images_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    for candidate in candidates_payload.get("candidates", []):
        existing_rgb = Path(candidate["rgb_path"]) if candidate.get("rgb_path") else None
        existing_nir = Path(candidate["nir_path"]) if candidate.get("nir_path") else None
        if (
            not force
            and existing_rgb is not None
            and existing_rgb.exists()
            and existing_nir is not None
            and existing_nir.exists()
        ):
            candidate["rgb_path"] = repo_path(existing_rgb)
            candidate["nir_path"] = repo_path(existing_nir)
            continue

        bbox = candidate.get("bbox") or candidate.get("window_bbox")
        if not bbox:
            continue
        image = _find_scene_image(candidate["date"], bbox)
        if image is None:
            continue

        spot_dir = output_root / candidate["spot_slug"]
        spot_dir.mkdir(parents=True, exist_ok=True)
        swell_height = candidate.get("swell_height_m") or 0.0
        swell_str = f"{float(swell_height):.1f}"
        base_name = f"{candidate['spot_slug']}_{candidate['date']}_{swell_str}m"
        for kind, vis in (("rgb", RGB_VIS), ("nir", NIR_VIS)):
            output_path = spot_dir / f"{base_name}_{kind}.png"
            if output_path.exists() and not force:
                candidate[f"{kind}_path"] = repo_path(output_path)
                continue
            url = image.getThumbURL(
                {
                    **vis,
                    "dimensions": IMAGE_WIDTH,
                    "region": bbox,
                    "format": "png",
                }
            )
            data = _fetch_thumbnail(url)
            if data is None:
                continue
            output_path.write_bytes(data)
            candidate[f"{kind}_path"] = repo_path(output_path)
    return candidates_payload


def write_review_template(
    candidates_payload: dict,
    *,
    reviews_path: Path | str,
) -> list[dict]:
    output_path = Path(reviews_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    existing_rows_by_id: dict[str, dict] = {}
    if output_path.exists():
        with output_path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                existing_rows_by_id[row["review_id"]] = row

    fieldnames = [
        "review_id",
        "spot_slug",
        "spot_name",
        "date",
        "source",
        "scene_source",
        "is_frozen_organized",
        "label",
        "note",
        "rgb_path",
        "annotated_rgb_path",
        "nir_path",
        "annotated_nir_path",
    ]
    rows: list[dict] = []
    for candidate in candidates_payload["candidates"]:
        existing = existing_rows_by_id.get(candidate["review_id"], {})
        rows.append(
            {
                "review_id": candidate["review_id"],
                "spot_slug": candidate["spot_slug"],
                "spot_name": candidate["spot_name"],
                "date": candidate["date"],
                "source": candidate["source"],
                "scene_source": candidate.get("scene_source") or "",
                "is_frozen_organized": str(candidate["is_frozen_organized"]).lower(),
                "label": existing.get("label", ""),
                "note": existing.get("note", ""),
                "rgb_path": candidate.get("rgb_path") or "",
                "annotated_rgb_path": candidate.get("annotated_rgb_path") or "",
                "nir_path": candidate.get("nir_path") or "",
                "annotated_nir_path": candidate.get("annotated_nir_path") or "",
            }
        )

    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def load_scene_reviews(path: Path | str) -> list[dict]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def validate_scene_reviews(candidates_payload: dict, review_rows: list[dict]) -> None:
    candidate_ids = [candidate["review_id"] for candidate in candidates_payload["candidates"]]
    review_ids = [row["review_id"] for row in review_rows]
    if review_ids != candidate_ids:
        raise ValueError("Review rows must match candidate order exactly.")

    seen_ids: set[str] = set()
    for row in review_rows:
        review_id = row["review_id"]
        if review_id in seen_ids:
            raise ValueError(f"Duplicate review row: {review_id}")
        seen_ids.add(review_id)
        label = (row.get("label") or "").strip()
        if label and label not in VALID_REVIEW_LABELS:
            raise ValueError(f"Invalid review label for {review_id}: {label}")


def summarize_scene_reviews(
    *,
    reviewed_scenes: list[dict],
    frozen_organized_labels: list[str],
) -> dict:
    total = len(reviewed_scenes)
    counts = {label: 0 for label in VALID_REVIEW_LABELS}
    for row in reviewed_scenes:
        counts[row["label"]] += 1

    clear_positive_share = (counts["clear_positive"] / total) if total else 0.0
    frozen_clear_positive_count = sum(1 for label in frozen_organized_labels if label == "clear_positive")

    if clear_positive_share >= 0.6:
        decision = "continue_optical_detector_research"
    elif clear_positive_share <= 0.3:
        decision = "close_sentinel2_optical_line"
    else:
        decision = "inconclusive_tighten_scene_selection"

    if counts["clear_negative"] > total / 2.0:
        interpretation = "sensor_or_use_case_problem"
    elif frozen_clear_positive_count >= 3:
        interpretation = "detector_problem"
    elif counts["clear_positive"] > counts["clear_negative"]:
        interpretation = "selection_problem"
    else:
        interpretation = "inconclusive"

    return {
        "decision": decision,
        "interpretation": interpretation,
        "reviewed_scene_count": total,
        "label_counts": counts,
        "clear_positive_share": clear_positive_share,
        "frozen_organized_clear_positive_count": frozen_clear_positive_count,
        "frozen_organized_scene_count": len(frozen_organized_labels),
    }


def build_summary(candidates_payload: dict, review_rows: list[dict]) -> dict:
    validate_scene_reviews(candidates_payload, review_rows)
    labeled_rows = [row for row in review_rows if (row.get("label") or "").strip()]
    frozen_labels = [row["label"] for row in review_rows if row["source"] == "frozen_organized" and row.get("label")]
    pending_review_ids = [row["review_id"] for row in review_rows if not (row.get("label") or "").strip()]

    summary = {
        "candidate_scene_count": len(candidates_payload["candidates"]),
        "labeled_scene_count": len(labeled_rows),
        "pending_scene_count": len(pending_review_ids),
        "pending_review_ids": pending_review_ids,
        "decision": "pending_manual_review",
        "interpretation": "pending_manual_review",
        "frozen_organized_clear_positive_count": None,
        "clear_positive_share": None,
        "label_counts": {label: 0 for label in VALID_REVIEW_LABELS},
    }
    if pending_review_ids:
        return summary

    full_summary = summarize_scene_reviews(
        reviewed_scenes=labeled_rows,
        frozen_organized_labels=frozen_labels,
    )
    return {
        **summary,
        **full_summary,
    }
