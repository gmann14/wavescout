#!/usr/bin/env python3
"""Phase 2, Script 1: Segment Nova Scotia coastline into candidate surf sections.

Downloads NS coastline from OpenStreetMap Overpass API, caches as GeoJSON,
then segments into 500m sections with 250m stride. Each segment gets a
centroid, orientation (compass bearing perpendicular to shore), and length.
Sheltered segments (exposure arc < 30 degrees) are filtered out.

Output: pipeline/data/coastline/ns_segments.geojson
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
from shapely.ops import linemerge, substring, unary_union
from shapely.strtree import STRtree
from shapely.prepared import prep

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "coastline"
RAW_CACHE = DATA_DIR / "ns_coastline.geojson"
OUTPUT_PATH = DATA_DIR / "ns_segments.geojson"

# Nova Scotia bounding box
BBOX = (43.3, -67.0, 47.1, -59.6)  # (south, west, north, east)

# Segmentation params
SEGMENT_LENGTH_M = 500
STRIDE_M = 250

# Minimum exposure arc (degrees) to keep a segment
MIN_EXPOSURE_ARC_DEG = 30

# Coordinate transformers: WGS84 <-> UTM 20N (covers most of NS)
TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32620", always_xy=True)
TO_WGS = Transformer.from_crs("EPSG:32620", "EPSG:4326", always_xy=True)


# ---------------------------------------------------------------------------
# Step 1: Download coastline from Overpass
# ---------------------------------------------------------------------------
def download_coastline() -> dict:
    """Query Overpass API for natural=coastline within the NS bbox.

    Splits the large bbox into sub-regions to avoid Overpass timeouts.
    Uses `out geom` to get way geometries directly (avoids expensive node resolution).
    Returns a dict with 'ways' key containing way geometries.
    """
    import time as _time

    south, west, north, east = BBOX

    # Split into sub-bboxes (4 lat x 8 lon = 32 tiles)
    lat_splits = np.linspace(south, north, 5)  # 4 rows
    lon_splits = np.linspace(west, east, 9)    # 8 cols

    all_ways: dict[int, list[tuple[float, float]]] = {}
    tile = 0
    total_tiles = (len(lat_splits) - 1) * (len(lon_splits) - 1)

    for i in range(len(lat_splits) - 1):
        for j in range(len(lon_splits) - 1):
            tile += 1
            s, n_ = lat_splits[i], lat_splits[i + 1]
            w, e = lon_splits[j], lon_splits[j + 1]

            query = f"""
            [out:json][timeout:300];
            way["natural"="coastline"]({s},{w},{n_},{e});
            out geom;
            """
            print(f"  Querying Overpass tile {tile}/{total_tiles} ({s:.1f},{w:.1f} to {n_:.1f},{e:.1f})...")
            if tile > 1:
                _time.sleep(5)  # Rate-limit Overpass queries

            endpoint = "https://overpass-api.de/api/interpreter"
            data = None
            for attempt in range(5):
                try:
                    resp = requests.post(
                        endpoint,
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

            if data is None:
                print(f"    WARN: Skipping tile {tile} after all retries failed")
                continue

            ways_in_tile = 0
            for el in data["elements"]:
                if el["type"] == "way" and "geometry" in el:
                    coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
                    if len(coords) >= 2:
                        all_ways[el["id"]] = coords
                        ways_in_tile += 1

            print(f"    Got {ways_in_tile} coastline ways")

    print(f"  Total unique coastline ways: {len(all_ways)}")
    return {"ways": all_ways}


def ways_to_geojson(data: dict) -> dict:
    """Convert downloaded ways dict to a GeoJSON FeatureCollection of LineStrings."""
    features = []
    for osm_id, coords in data["ways"].items():
        if len(coords) >= 2:
            features.append(
                {
                    "type": "Feature",
                    "properties": {"osm_id": int(osm_id)},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords,
                    },
                }
            )

    print(f"  Converted to {len(features)} LineString features")
    return {"type": "FeatureCollection", "features": features}


def load_or_download_coastline() -> dict:
    """Load cached coastline or download from Overpass."""
    if RAW_CACHE.exists():
        print(f"Loading cached coastline from {RAW_CACHE}")
        with RAW_CACHE.open() as f:
            return json.load(f)

    data = download_coastline()
    geojson = ways_to_geojson(data)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with RAW_CACHE.open("w") as f:
        json.dump(geojson, f)
    print(f"  Cached coastline to {RAW_CACHE}")
    return geojson


# ---------------------------------------------------------------------------
# Step 2: Merge and segment
# ---------------------------------------------------------------------------
def extract_coastline_lines(geojson: dict) -> list[LineString]:
    """Extract LineStrings from coastline GeoJSON.

    We intentionally do NOT merge lines (linemerge) because merged lines
    can have 200k+ coords and make substring() extremely slow. Individual
    OSM ways are short enough to segment efficiently.
    """
    lines = []
    for feat in geojson["features"]:
        geom = shape(feat["geometry"])
        if isinstance(geom, LineString) and len(geom.coords) >= 2:
            lines.append(geom)
        elif isinstance(geom, MultiLineString):
            for part in geom.geoms:
                if len(part.coords) >= 2:
                    lines.append(part)

    print(f"  Extracted {len(lines)} coastline LineStrings")
    return lines


def line_to_utm(line: LineString) -> LineString:
    """Project a WGS84 LineString to UTM 20N."""
    coords = [TO_UTM.transform(x, y) for x, y in line.coords]
    return LineString(coords)


def line_to_wgs(line: LineString) -> LineString:
    """Project a UTM 20N LineString back to WGS84."""
    coords = [TO_WGS.transform(x, y) for x, y in line.coords]
    return LineString(coords)


def segment_line(line_utm: LineString) -> list[LineString]:
    """Cut a UTM line into SEGMENT_LENGTH_M segments with STRIDE_M stride.

    Uses shapely's optimized substring() for efficient sub-line extraction.
    """
    total_length = line_utm.length
    segments = []
    offset = 0.0

    while offset + SEGMENT_LENGTH_M <= total_length:
        sub = substring(line_utm, offset, offset + SEGMENT_LENGTH_M)
        if sub is not None and not sub.is_empty and sub.length > 0:
            segments.append(sub)
        offset += STRIDE_M

    return segments


# ---------------------------------------------------------------------------
# Step 3: Compute orientation and exposure
# ---------------------------------------------------------------------------
def compute_bearing(line_utm: LineString) -> float:
    """Compute compass bearing of a line segment (degrees, 0=N, clockwise).

    Returns the bearing from the first to last point.
    """
    coords = list(line_utm.coords)
    dx = coords[-1][0] - coords[0][0]
    dy = coords[-1][1] - coords[0][1]
    bearing = math.degrees(math.atan2(dx, dy)) % 360
    return bearing


def shore_normal_seaward(
    line_bearing: float,
    line_utm: LineString,
    nearby_coastline: list[LineString],
) -> float:
    """Compute seaward-facing normal bearing.

    The perpendicular to a coastline segment has two directions. We pick the
    one that points away from land (seaward). Heuristic: the seaward side is
    the one where a point offset along the normal is farther from other
    coastline segments.
    """
    centroid = line_utm.interpolate(0.5, normalized=True)
    cx, cy = centroid.x, centroid.y

    # Two candidate normals: +90 and -90 from line bearing
    for sign in [1, -1]:
        normal_bearing = (line_bearing + sign * 90) % 360
        rad = math.radians(normal_bearing)
        test_x = cx + 200 * math.sin(rad)
        test_y = cy + 200 * math.cos(rad)
        test_pt = Point(test_x, test_y)
        dist = min((line.distance(test_pt) for line in nearby_coastline), default=999999)
        if sign == 1:
            dist_pos = dist
            bearing_pos = normal_bearing
        else:
            dist_neg = dist
            bearing_neg = normal_bearing

    # The normal pointing farther from other coastline is seaward
    if dist_pos >= dist_neg:
        return bearing_pos
    return bearing_neg


def compute_exposure_arc(
    centroid_utm: tuple[float, float],
    nearby_prepared: object,
    normal_bearing: float,
    radius_m: float = 5000.0,
) -> float:
    """Compute open-ocean exposure arc in degrees.

    Casts rays from the centroid outward. An arc is "exposed" if the ray
    doesn't intersect coastline within radius_m. Returns the total degrees
    of unblocked arc within ±90° of the seaward normal.

    Uses a prepared geometry for fast intersection tests.
    """
    cx, cy = centroid_utm
    open_degrees = 0
    step = 5  # degree resolution (coarsened for speed)

    for angle_offset in range(-90, 91, step):
        ray_bearing = (normal_bearing + angle_offset) % 360
        rad = math.radians(ray_bearing)
        end_x = cx + radius_m * math.sin(rad)
        end_y = cy + radius_m * math.cos(rad)
        ray = LineString([(cx, cy), (end_x, end_y)])

        if not nearby_prepared.intersects(ray):
            open_degrees += step

    return open_degrees


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("Phase 2, Step 1: Segment Nova Scotia Coastline")
    print("=" * 60)

    # Load coastline
    geojson = load_or_download_coastline()
    lines_wgs = extract_coastline_lines(geojson)

    # Project to UTM
    print("Projecting to UTM 20N...")
    lines_utm = [line_to_utm(line) for line in lines_wgs]

    # Build spatial index for fast nearby-coastline queries
    print("Building spatial index for coastline...")
    all_lines_utm = lines_utm  # keep all for the spatial index
    coastline_tree = STRtree(all_lines_utm)

    # Filter out very short lines (< segment length) for segmentation only
    lines_for_seg = [l for l in lines_utm if l.length >= SEGMENT_LENGTH_M]
    print(f"  {len(lines_for_seg)} lines >= {SEGMENT_LENGTH_M}m (of {len(all_lines_utm)} total)")

    # Segment each line
    print(f"Segmenting with {SEGMENT_LENGTH_M}m length, {STRIDE_M}m stride...")
    all_segments_utm: list[LineString] = []
    for line in lines_for_seg:
        segs = segment_line(line)
        all_segments_utm.extend(segs)
    print(f"  Generated {len(all_segments_utm)} raw segments")

    # Compute properties and filter by exposure
    print("Computing orientation and exposure for each segment...")
    features = []
    kept = 0
    filtered_sheltered = 0
    exposure_radius = 5000.0

    for i, seg_utm in enumerate(all_segments_utm):
        if (i + 1) % 200 == 0 or i == 0:
            print(f"  Processing segment {i + 1}/{len(all_segments_utm)} (kept={kept}, filtered={filtered_sheltered})...")

        centroid_utm_pt = seg_utm.interpolate(0.5, normalized=True)
        cx, cy = centroid_utm_pt.x, centroid_utm_pt.y

        # Query nearby coastline within exposure_radius using spatial index
        search_area = Point(cx, cy).buffer(exposure_radius)
        nearby_idxs = coastline_tree.query(search_area)
        nearby_lines = [all_lines_utm[j] for j in nearby_idxs]

        if not nearby_lines:
            # No coastline nearby — likely an island edge, skip
            filtered_sheltered += 1
            continue

        bearing = compute_bearing(seg_utm)
        normal = shore_normal_seaward(bearing, seg_utm, nearby_lines)

        # Merge nearby lines and prepare for fast intersection
        nearby_merged = unary_union(nearby_lines)
        nearby_prepared = prep(nearby_merged)

        exposure_arc = compute_exposure_arc(
            (cx, cy),
            nearby_prepared,
            normal,
            radius_m=exposure_radius,
        )

        if exposure_arc < MIN_EXPOSURE_ARC_DEG:
            filtered_sheltered += 1
            continue

        # Convert segment back to WGS84
        seg_wgs = line_to_wgs(seg_utm)
        centroid_wgs_pt = seg_wgs.interpolate(0.5, normalized=True)

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "segment_id": f"ns-seg-{kept:05d}",
                    "centroid_lat": round(centroid_wgs_pt.y, 6),
                    "centroid_lon": round(centroid_wgs_pt.x, 6),
                    "orientation_deg": round(normal, 1),
                    "shore_bearing_deg": round(bearing, 1),
                    "exposure_arc_deg": round(exposure_arc, 1),
                    "length_m": round(seg_utm.length, 1),
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [round(x, 6), round(y, 6)] for x, y in seg_wgs.coords
                    ],
                },
            }
        )
        kept += 1

    print(f"\n  Kept: {kept} segments")
    print(f"  Filtered (sheltered): {filtered_sheltered}")

    output = {"type": "FeatureCollection", "features": features}

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        json.dump(output, f)
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
