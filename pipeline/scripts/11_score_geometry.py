#!/usr/bin/env python3
"""Phase 2, Script 2: Score coastline segments using transparent geometry heuristics.

Loads segmented coastline from ns_segments.geojson and scores each segment
on a 0-100 scale using four components:

  - Swell exposure (faces 140-200° for Atlantic swell): 40 pts max
  - Favorable geometry (headland/bay proximity): 25 pts max
  - Bathymetric gradient (GEBCO netCDF if available, else skip): 20 pts max
  - Road access proximity (nearest OSM road): 15 pts max

Output: pipeline/data/coastline/ns_scored_segments.geojson
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import requests
from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString, Point, shape
from shapely.ops import nearest_points
from shapely.strtree import STRtree

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "coastline"
SEGMENTS_PATH = DATA_DIR / "ns_segments.geojson"
OUTPUT_PATH = DATA_DIR / "ns_scored_segments.geojson"

# UTM 20N transformers
TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32620", always_xy=True)
TO_WGS = Transformer.from_crs("EPSG:32620", "EPSG:4326", always_xy=True)

# ---------------------------------------------------------------------------
# Score 1: Swell Exposure (40 pts max)
# ---------------------------------------------------------------------------
# Ideal facing for Atlantic swell hitting Nova Scotia: ~140-200° (SSE to S)
IDEAL_SWELL_CENTER = 170.0  # degrees (roughly south)
IDEAL_SWELL_HALF_WIDTH = 30.0  # degrees each side => 140-200 range


def score_swell_exposure(orientation_deg: float, exposure_arc_deg: float) -> tuple[float, str]:
    """Score how well the segment faces dominant Atlantic swell.

    Max 40 points when the segment faces directly into the 140-200° window
    with full ocean exposure.
    """
    # Angular distance from ideal swell direction
    diff = abs(((orientation_deg - IDEAL_SWELL_CENTER + 180) % 360) - 180)

    if diff <= IDEAL_SWELL_HALF_WIDTH:
        direction_score = 1.0
    elif diff <= IDEAL_SWELL_HALF_WIDTH + 30:
        # Linear falloff in the next 30°
        direction_score = 1.0 - (diff - IDEAL_SWELL_HALF_WIDTH) / 30.0
    elif diff <= IDEAL_SWELL_HALF_WIDTH + 60:
        # Slow falloff for oblique angles
        direction_score = 0.5 * (1.0 - (diff - IDEAL_SWELL_HALF_WIDTH - 30) / 30.0)
    else:
        direction_score = 0.0

    # Exposure arc factor: more open = better
    exposure_factor = min(exposure_arc_deg / 120.0, 1.0)

    raw = direction_score * exposure_factor * 40.0

    # Build explanation
    if direction_score >= 0.8:
        explanation = f"Faces {orientation_deg:.0f}° — directly into Atlantic swell window"
    elif direction_score >= 0.4:
        explanation = f"Faces {orientation_deg:.0f}° — oblique to primary swell"
    else:
        explanation = f"Faces {orientation_deg:.0f}° — poor alignment with Atlantic swell"

    return round(raw, 1), explanation


# ---------------------------------------------------------------------------
# Score 2: Favorable Geometry - Headland/Bay (25 pts max)
# ---------------------------------------------------------------------------
def score_geometry(
    centroid_utm: tuple[float, float],
    seg_utm: LineString,
    coastline_tree: object,
    coastline_lines: list[LineString],
) -> tuple[float, str]:
    """Score coastal geometry for surf-favorable features.

    Headlands focus swell energy. Bays provide shelter and refraction.
    A segment near a concave-convex transition scores higher.
    Uses spatial index for efficient nearby coastline queries.
    """
    cx, cy = centroid_utm
    center_pt = Point(cx, cy)

    # Query coastline within 2km using spatial index
    outer_radius = 2000.0
    inner_radius = 500.0
    search_area = center_pt.buffer(outer_radius)
    nearby_idxs = coastline_tree.query(search_area)

    coastline_nearby = 0.0
    inner_circle = center_pt.buffer(inner_radius)
    outer_ring = search_area.difference(inner_circle)

    for idx in nearby_idxs:
        line = coastline_lines[idx]
        clipped = line.intersection(outer_ring)
        if not clipped.is_empty:
            coastline_nearby += clipped.length

    complexity_score = min(coastline_nearby / 6000.0, 1.0)

    # Check if the segment itself has curvature (bending)
    seg_coords = list(seg_utm.coords)
    if len(seg_coords) >= 3:
        straight = math.dist(seg_coords[0], seg_coords[-1])
        sinuosity = seg_utm.length / straight if straight > 0 else 1.0
        curvature_bonus = min((sinuosity - 1.0) * 5.0, 0.3)
    else:
        curvature_bonus = 0.0

    raw = (complexity_score + curvature_bonus) * 25.0
    raw = min(raw, 25.0)

    if complexity_score >= 0.6:
        explanation = "Complex coastal geometry nearby (headland/bay features)"
    elif complexity_score >= 0.3:
        explanation = "Moderate coastal complexity"
    else:
        explanation = "Relatively straight, open coastline"

    return round(raw, 1), explanation


# ---------------------------------------------------------------------------
# Score 3: Bathymetric Gradient (20 pts max)
# ---------------------------------------------------------------------------
def try_load_gebco() -> object | None:
    """Try to load GEBCO bathymetry NetCDF. Returns None if not available."""
    try:
        import netCDF4
        gebco_path = DATA_DIR.parent / "gebco" / "gebco_ns.nc"
        if gebco_path.exists():
            return netCDF4.Dataset(str(gebco_path))
    except ImportError:
        pass
    return None


def score_bathymetry(
    centroid_lon: float, centroid_lat: float, gebco_ds: object | None
) -> tuple[float, str]:
    """Score bathymetric gradient offshore of the segment.

    Steeper nearshore gradients often correlate with better wave quality.
    If GEBCO data is unavailable, returns 0 with explanation.
    """
    if gebco_ds is None:
        return 0.0, "Bathymetry data not available (GEBCO not loaded)"

    try:
        lats = gebco_ds.variables["lat"][:]
        lons = gebco_ds.variables["lon"][:]
        elevation = gebco_ds.variables["elevation"]

        lat_idx = int(np.argmin(np.abs(lats - centroid_lat)))
        lon_idx = int(np.argmin(np.abs(lons - centroid_lon)))

        # Sample depths at increasing distances offshore (roughly)
        # Use a 5-pixel transect
        depths = []
        for offset in range(5):
            li = min(lat_idx + offset, len(lats) - 1)
            val = float(elevation[li, lon_idx])
            if val < 0:  # underwater
                depths.append(abs(val))

        if len(depths) >= 2:
            gradient = (depths[-1] - depths[0]) / (len(depths) * 500)
            score = min(gradient / 0.05, 1.0) * 20.0
            explanation = f"Nearshore gradient: {gradient:.3f} m/m"
        else:
            score = 5.0
            explanation = "Shallow nearshore area"

        return round(score, 1), explanation

    except Exception:
        return 0.0, "Bathymetry lookup failed"


# ---------------------------------------------------------------------------
# Score 4: Road Access Proximity (15 pts max)
# ---------------------------------------------------------------------------
ROADS_CACHE_PATH = DATA_DIR.parent / "coastline" / "ns_roads_utm.json"
_road_tree: STRtree | None = None
_road_lines: list[LineString] = []


def download_ns_roads() -> list[LineString]:
    """Download NS roads from Overpass in tiled batches, cache locally."""
    import time as _time

    # NS bbox: 43.3,-67.0 to 47.1,-59.6
    # Use 4x4 = 16 tiles for manageable Overpass queries
    lat_splits = np.linspace(43.3, 47.1, 5)
    lon_splits = np.linspace(-67.0, -59.6, 5)

    all_ways: dict[int, list[tuple[float, float]]] = {}
    tile = 0
    total_tiles = 16

    for i in range(len(lat_splits) - 1):
        for j in range(len(lon_splits) - 1):
            tile += 1
            s, n_ = lat_splits[i], lat_splits[i + 1]
            w, e = lon_splits[j], lon_splits[j + 1]

            query = f"""
            [out:json][timeout:300];
            way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified)$"]({s},{w},{n_},{e});
            out geom;
            """
            print(f"  Fetching roads tile {tile}/{total_tiles}...")
            if tile > 1:
                _time.sleep(5)

            for attempt in range(4):
                try:
                    resp = requests.post(
                        "https://overpass-api.de/api/interpreter",
                        data={"data": query},
                        timeout=300,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except (requests.HTTPError, requests.Timeout,
                        requests.ConnectionError, requests.JSONDecodeError) as exc:
                    wait = 10 * (attempt + 1)
                    print(f"    Attempt {attempt + 1} failed ({type(exc).__name__}), retrying in {wait}s...")
                    _time.sleep(wait)
                    data = None

            if data is None:
                print(f"    WARN: Skipping roads tile {tile}")
                continue

            ways_count = 0
            for el in data["elements"]:
                if el["type"] == "way" and "geometry" in el:
                    coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
                    if len(coords) >= 2:
                        all_ways[el["id"]] = coords
                        ways_count += 1
            print(f"    Got {ways_count} road ways")

    print(f"  Total unique road ways: {len(all_ways)}")

    # Convert to UTM and cache
    lines = []
    for coords in all_ways.values():
        utm_coords = [TO_UTM.transform(x, y) for x, y in coords]
        lines.append(LineString(utm_coords))

    # Cache the UTM road coords as JSON for reuse
    cache_data = []
    for coords in all_ways.values():
        utm_coords = [list(TO_UTM.transform(x, y)) for x, y in coords]
        cache_data.append(utm_coords)

    ROADS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ROADS_CACHE_PATH.open("w") as f:
        json.dump(cache_data, f)
    print(f"  Cached roads to {ROADS_CACHE_PATH}")

    return lines


def load_road_tree() -> tuple[STRtree, list[LineString]]:
    """Load or download NS roads and build a spatial index."""
    global _road_tree, _road_lines

    if _road_tree is not None:
        return _road_tree, _road_lines

    if ROADS_CACHE_PATH.exists():
        print("Loading cached road data...")
        with ROADS_CACHE_PATH.open() as f:
            cache_data = json.load(f)
        _road_lines = [LineString(coords) for coords in cache_data]
    else:
        print("Downloading NS road network from Overpass...")
        _road_lines = download_ns_roads()

    print(f"  Building road spatial index ({len(_road_lines)} roads)...")
    _road_tree = STRtree(_road_lines)
    return _road_tree, _road_lines


def score_road_access(
    centroid_utm: tuple[float, float],
    road_tree: STRtree,
    road_lines: list[LineString],
) -> tuple[float, str]:
    """Score proximity to nearest road. Closer = higher score (15 pts max)."""
    cx, cy = centroid_utm
    pt = Point(cx, cy)

    # Search for roads within 5km
    search_area = pt.buffer(5000)
    nearby_idxs = road_tree.query(search_area)

    if len(nearby_idxs) == 0:
        return 0.0, "No road within 5km"

    min_dist = min(road_lines[j].distance(pt) for j in nearby_idxs)

    # Scoring: < 200m = full marks, linear falloff to 5km
    if min_dist <= 200:
        score = 15.0
        explanation = f"Road access within {min_dist:.0f}m"
    elif min_dist <= 5000:
        score = 15.0 * (1.0 - (min_dist - 200) / 4800)
        explanation = f"Road {min_dist:.0f}m away"
    else:
        score = 0.0
        explanation = f"No road within 5km (nearest: {min_dist:.0f}m)"

    return round(score, 1), explanation


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("Phase 2, Step 2: Score Geometry Heuristics")
    print("=" * 60)

    if not SEGMENTS_PATH.exists():
        print(f"ERROR: {SEGMENTS_PATH} not found. Run 10_segment_coastline.py first.")
        sys.exit(1)

    with SEGMENTS_PATH.open() as f:
        segments = json.load(f)

    n = len(segments["features"])
    print(f"Loaded {n} segments")

    # Rebuild coastline UTM for geometry scoring with spatial index
    print("Rebuilding coastline UTM geometry with spatial index...")
    all_lines_utm = []
    for feat in segments["features"]:
        coords = feat["geometry"]["coordinates"]
        utm_coords = [TO_UTM.transform(x, y) for x, y in coords]
        all_lines_utm.append(LineString(utm_coords))
    coastline_tree = STRtree(all_lines_utm)

    # Try loading GEBCO
    gebco_ds = try_load_gebco()
    if gebco_ds:
        print("GEBCO bathymetry loaded")
    else:
        print("GEBCO not available — bathymetry score will be 0 for all segments")

    # Load road network
    road_tree, road_lines = load_road_tree()

    # Score each segment
    print(f"\nScoring {n} segments...")

    for i, feat in enumerate(segments["features"]):
        props = feat["properties"]

        if (i + 1) % 500 == 0 or i == 0:
            print(f"  Scoring segment {i + 1}/{n}...")

        orientation = props["orientation_deg"]
        exposure_arc = props["exposure_arc_deg"]
        clat = props["centroid_lat"]
        clon = props["centroid_lon"]
        cx, cy = TO_UTM.transform(clon, clat)

        seg_coords = [(TO_UTM.transform(x, y)) for x, y in feat["geometry"]["coordinates"]]
        seg_utm = LineString(seg_coords)

        # Score components
        swell_score, swell_expl = score_swell_exposure(orientation, exposure_arc)
        geom_score, geom_expl = score_geometry((cx, cy), seg_utm, coastline_tree, all_lines_utm)
        bathy_score, bathy_expl = score_bathymetry(clon, clat, gebco_ds)
        road_score, road_expl = score_road_access((cx, cy), road_tree, road_lines)

        total = swell_score + geom_score + bathy_score + road_score

        # Build explanation
        highlights = []
        if swell_score >= 30:
            highlights.append("Excellent swell exposure")
        elif swell_score >= 20:
            highlights.append("Good swell alignment")
        if geom_score >= 15:
            highlights.append("Favorable coastal geometry")
        if road_score >= 10:
            highlights.append("Good road access")

        caveats = []
        if bathy_score == 0:
            caveats.append("No bathymetry data available")
        if road_score == 0:
            caveats.append("Remote — no nearby road access")
        if exposure_arc < 60:
            caveats.append("Limited ocean exposure")

        props["total_score"] = round(total, 1)
        props["swell_exposure_score"] = swell_score
        props["geometry_score"] = geom_score
        props["bathymetry_score"] = bathy_score
        props["road_access_score"] = road_score
        props["explanation"] = {
            "summary": f"Score {total:.0f}/100 — {swell_expl}",
            "score_components": {
                "swell_exposure": f"{swell_score}/40 — {swell_expl}",
                "geometry": f"{geom_score}/25 — {geom_expl}",
                "bathymetry": f"{bathy_score}/20 — {bathy_expl}",
                "road_access": f"{road_score}/15 — {road_expl}",
            },
            "highlights": highlights,
            "caveats": caveats,
        }

    # Sort by total score descending
    segments["features"].sort(
        key=lambda f: f["properties"]["total_score"], reverse=True
    )

    # Re-rank
    for i, feat in enumerate(segments["features"]):
        feat["properties"]["rank"] = i + 1

    with OUTPUT_PATH.open("w") as f:
        json.dump(segments, f)
    print(f"\nWrote {OUTPUT_PATH}")

    # Summary stats
    scores = [f["properties"]["total_score"] for f in segments["features"]]
    print(f"\nScore distribution:")
    print(f"  Min:    {min(scores):.1f}")
    print(f"  Max:    {max(scores):.1f}")
    print(f"  Median: {sorted(scores)[len(scores) // 2]:.1f}")
    print(f"  Mean:   {sum(scores) / len(scores):.1f}")

    # Top 10
    print(f"\nTop 10 segments:")
    for feat in segments["features"][:10]:
        p = feat["properties"]
        print(
            f"  #{p['rank']} {p['segment_id']}: "
            f"score={p['total_score']}, "
            f"lat={p['centroid_lat']}, lon={p['centroid_lon']}, "
            f"facing={p['orientation_deg']}°"
        )


if __name__ == "__main__":
    main()
