# Spec: Bathymetry Integration

> Add seafloor depth data to the geometry scoring pipeline, filling in the currently-skipped 20-point bathymetry component.

## Problem

Script 11 (`score_geometry.py`) scores coastline segments on a 0-100 scale with four components. The bathymetry component (worth 20 points) is currently skipped because no bathymetry data source was integrated:

```
Swell exposure:       40 pts  ✅ implemented
Coastal complexity:   25 pts  ✅ implemented
Bathymetry gradient:  20 pts  ❌ skipped (no GEBCO data)
Road access:          15 pts  ✅ implemented
```

This means the effective scoring range is 0-80 instead of 0-100, and segments with favorable seafloor profiles (gradual shoaling that focuses wave energy) receive no credit for it.

Bathymetry matters for surfing because:
- **Gradual nearshore slope** creates well-formed, peeling waves (good for surfing)
- **Steep nearshore slope** creates dumping shore break or closeouts (poor for surfing)
- **Offshore reefs/ridges** focus swell energy onto specific coastline segments
- **Deep channels** can block swell from reaching the shore

## Data Sources

### Option A (Recommended): GEBCO 2024

The General Bathymetric Chart of the Oceans provides global seafloor elevation.

| Aspect | Details |
|--------|---------|
| Resolution | 15 arc-seconds (~450m at NS latitudes) |
| Coverage | Global, complete for NS coast |
| Format | NetCDF or GeoTIFF |
| Access | Free download from `gebco.net`, or via GEE (`projects/sat-io/open-datasets/gebco/gebco_grid`) |
| Quality | Compiled from ship soundings + satellite altimetry. Good offshore, coarser nearshore. |

**Limitation**: 450m resolution is coarse for nearshore slope analysis. A single pixel spans the entire surf zone. However, it captures the broader continental shelf gradient and offshore features.

### Option B: CHS Nautical Charts (Canadian Hydrographic Service)

| Aspect | Details |
|--------|---------|
| Resolution | Variable — detailed in navigable waters, sparse offshore |
| Coverage | Canadian waters, good coverage of NS harbors and approaches |
| Format | S-57 vector charts with depth soundings + contours |
| Access | Free via CHS online viewer, bulk download requires license |
| Quality | Very accurate nearshore (from ship surveys), but vector format requires processing |

**Limitation**: Vector chart data is harder to work with programmatically. Would need to interpolate depth soundings into a raster grid for per-segment analysis. Coverage is patchy — detailed in harbors, sparse along open coastline (which is exactly where surf breaks are).

### Option C: ETOPO 2022

| Aspect | Details |
|--------|---------|
| Resolution | 15 arc-seconds (same as GEBCO) |
| Coverage | Global |
| Access | Available in GEE as `NOAA/NGDC/ETOPO1` (older version) |

Similar to GEBCO but less frequently updated. GEBCO is preferred.

### Option D: Multibeam survey data

High-resolution seafloor mapping from research vessels. Sub-meter resolution where available, but extremely patchy coverage. Not practical as a systematic data source.

**Recommendation**: GEBCO via GEE for the initial implementation. It provides complete coverage with minimal setup since GEE handles the data access. Accept the 450m resolution limitation and focus on shelf-scale features rather than surf-zone-scale features.

## What to Extract

For each coastline segment, extract bathymetric metrics at three distance bands from shore:

### Depth at fixed distances

| Distance from shore | What it tells us |
|---------------------|-----------------|
| 100m | Immediate nearshore — very shallow if good surf zone exists |
| 200m | Outer surf zone — where swell begins to feel the bottom |
| 500m | Approach zone — swell refraction and focusing happens here |
| 1000m | Continental shelf — general depth context |

### Derived metrics

1. **Nearshore slope gradient** (`slope_100_500`): Depth change between 100m and 500m offshore, divided by distance. Steeper = waves break harder and faster. Moderate slope (1:50 to 1:100) is ideal for surfing.

```python
slope = (depth_500m - depth_100m) / 400  # meters depth per meter distance
```

2. **Shelf gradient** (`slope_500_1000`): Broader continental shelf slope. Gradual shelf = more swell energy reaches shore.

3. **Depth anomaly** (`depth_anomaly_500`): Is this segment's 500m depth shallower or deeper than its neighbors? Shallow anomalies suggest underwater ridges that focus swell energy.

```python
depth_anomaly = segment_depth_500 - mean_neighbor_depth_500
# Negative = shallower than neighbors = potential swell focusing
```

4. **Offshore feature detection**: Look for abrupt depth changes (>5m over 450m) within 2km of shore. These indicate reefs, ridges, or channels.

## Scoring Integration

### Bathymetry sub-score (0-20 points)

```python
def score_bathymetry(depth_100, depth_200, depth_500, depth_1000, neighbor_depths):
    score = 0.0

    # 1. Nearshore slope (8 pts max)
    # Ideal: moderate slope 1:50 to 1:100 (0.01 to 0.02 m/m)
    slope = (depth_500 - depth_100) / 400
    if slope is None or depth_100 is None or depth_500 is None:
        slope_score = 0.0  # no data
    elif 0.01 <= abs(slope) <= 0.02:
        slope_score = 1.0  # ideal
    elif 0.005 <= abs(slope) <= 0.03:
        slope_score = 0.6  # acceptable
    elif abs(slope) < 0.005:
        slope_score = 0.3  # very flat — waves don't break well
    else:
        slope_score = 0.2  # too steep — closeouts
    score += slope_score * 8

    # 2. Approach depth (6 pts max)
    # Deeper approach = more swell energy arrives. Shallow approach = swell dissipated.
    if depth_500 is not None:
        if abs(depth_500) >= 15:
            approach_score = 1.0  # deep approach
        elif abs(depth_500) >= 8:
            approach_score = 0.6
        else:
            approach_score = 0.3  # very shallow — swell breaks far out
    else:
        approach_score = 0.0
    score += approach_score * 6

    # 3. Swell focusing (6 pts max)
    # Shallower than neighbors = potential swell focus
    if neighbor_depths and depth_500 is not None:
        mean_neighbor = np.mean(neighbor_depths)
        anomaly = depth_500 - mean_neighbor  # negative = shallower
        if anomaly < -3:
            focus_score = 1.0  # significant ridge/shoal
        elif anomaly < -1:
            focus_score = 0.5  # slight focusing
        else:
            focus_score = 0.2  # no focusing advantage
    else:
        focus_score = 0.0
    score += focus_score * 6

    return round(score, 1)
```

### Handling missing data

At 450m resolution, some nearshore pixels (especially at 100m from shore) will fall on land. Handle this:
- If `depth_100` is on land (positive elevation): skip nearshore slope, score only approach depth + focusing
- If all depths are null: score 0 for bathymetry (same as current behavior)
- Scale the 20 points proportionally based on how many sub-metrics have data

## Pipeline Integration

### Option A (Recommended): Update script 11

Add bathymetry scoring directly to `11_score_geometry.py`:

1. Load GEBCO data (download NetCDF once, cache locally like coastline data)
2. For each segment, compute seaward sample points at 100m, 200m, 500m, 1000m
3. Extract depth at each point from GEBCO grid
4. Compute bathymetry sub-score
5. Add to total geometry score

This fills in the existing 20-point gap without changing the scoring architecture.

### Option B: New script `25b_add_bathymetry.py`

Standalone script that enriches segments with bathymetry data, then script 11 reads the enriched data.

**Recommendation**: Option A — the bathymetry component was always designed to be part of script 11. Adding it there is the natural fit.

### GEE approach (alternative to local NetCDF)

```python
gebco = ee.Image("projects/sat-io/open-datasets/gebco/gebco_grid")

# Sample point 500m seaward from segment midpoint
seaward_point = segment_midpoint.offset(500, exposure_direction)
depth_500 = gebco.sample(seaward_point, scale=450).first().get('b1')
```

All server-side, no large downloads. But adds GEE dependency to script 11 (which currently runs locally).

### Local NetCDF approach (preferred)

```python
# Download GEBCO tile for NS once (~200MB)
# pip install netCDF4
from netCDF4 import Dataset

gebco = Dataset("pipeline/data/bathymetry/gebco_2024_ns.nc")
lat = gebco.variables['lat'][:]
lon = gebco.variables['lon'][:]
elevation = gebco.variables['elevation'][:]  # negative = below sea level

def get_depth(lat, lon):
    # Find nearest grid cell
    lat_idx = np.argmin(np.abs(lat - target_lat))
    lon_idx = np.argmin(np.abs(lon - target_lon))
    return elevation[lat_idx, lon_idx]  # negative meters
```

**Pros**: Fast (local lookup), no GEE dependency, works offline.
**Cons**: Requires downloading and caching the GEBCO tile.

**Recommendation**: Local NetCDF. Script 11 currently runs locally with no GEE dependency. Keep it that way. Download the NS GEBCO subset once (~200MB) and cache in `pipeline/data/bathymetry/`.

## Seaward Sample Point Calculation

To sample bathymetry offshore from each segment, compute points perpendicular to the coastline heading seaward:

```python
def seaward_point(segment_midpoint, orientation_deg, distance_m):
    """Compute a point offshore from a coastline segment.

    orientation_deg: direction the coast faces (outward normal)
    distance_m: how far offshore
    """
    # The segment's orientation is the direction it faces (seaward)
    # Use UTM projection for accurate distance
    mid_utm = TO_UTM.transform(segment_midpoint.x, segment_midpoint.y)
    dx = distance_m * math.sin(math.radians(orientation_deg))
    dy = distance_m * math.cos(math.radians(orientation_deg))
    offshore_utm = (mid_utm[0] + dx, mid_utm[1] + dy)
    return TO_WGS.transform(*offshore_utm)
```

The segment orientation (outward-facing direction) is already computed in script 10/11.

## Expected Improvement to Spot Ranking

### Current state (without bathymetry)

- Max possible score: 80 (not 100)
- All segments miss the same 20 points — no differentiation on seafloor
- Known spots with favorable bathymetry (gradual sandbars at Lawrencetown, reef at Cow Bay) get no credit

### After bathymetry integration

- Max possible score: 100 (full range)
- Beach break spots with gradual nearshore slopes gain 12-18 points
- Cliff-backed deep-water segments gain only 2-6 points (steep nearshore = low score)
- Expected: known spots move from 88-94th percentile to 90-96th percentile (slight improvement as their favorable bathymetry gets rewarded)

### Validation

Re-run `12_calibrate.py` after adding bathymetry scores:
- Do known spots still rank in top 10%?
- Do any known spots drop significantly? (Would indicate a scoring bug)
- Does the score distribution spread out? (More differentiation = better)

## Effort Estimate

| Task | Time |
|------|------|
| GEBCO data download + processing | 1-2h |
| Seaward sample point computation | 1h |
| Bathymetry scoring logic | 2-3h |
| Integration into script 11 | 1-2h |
| Re-scoring all segments | 0.5h (runtime) |
| Recalibration + validation | 1-2h |
| build_web_data.py update (include bathy metrics) | 0.5h |
| **Total** | **7-11h** |

## Dependencies

- Segment data with orientation from `10_segment_coastline.py` (done)
- Geometry scoring framework in `11_score_geometry.py` (done — has placeholder for bathymetry)
- GEBCO 2024 data (free download, needs ~200MB local storage)
- `netCDF4` Python package (add to requirements)
- Calibration spots in `12_calibrate.py` (done)

## Open Questions

1. **Is 450m resolution useful at all for surf zone analysis?** The surf zone is 50-200m wide. GEBCO's resolution captures continental shelf features but not sandbars or reef structure. It may only provide a coarse "this area has reasonable depth" signal, not fine-grained surf quality information.
2. **Should we try CHS chart data for the ~20 configured spots?** CHS has detailed nearshore soundings for some areas. Could extract high-quality bathymetry for known spots while using GEBCO for the full coastline.
3. **GEBCO land/sea boundary accuracy**: Near the coast, GEBCO cells may blend land and sea elevations. Need to verify that 100m offshore samples actually return negative (underwater) values, not interpolated land elevation.
4. **Dynamic bathymetry**: Sandbars shift seasonally. GEBCO is a static snapshot. For beach breaks, the bathymetry that matters (sandbars) changes constantly. Fixed bathymetry scoring is most useful for reef and point breaks where the seafloor is stable.
5. **Weight rebalancing**: Adding 20 points of bathymetry to the score changes the relative importance of other components. Should we rebalance? E.g., if bathymetry is weak signal due to resolution limits, maybe it should be 10 points instead of 20.
