# Spec: Cliff Foam Filter

> Use elevation and slope data to classify coastline type (beach vs. cliff vs. headland) and weight foam detections accordingly, reducing false positives from cliff impact foam.

## Problem

Wave impact on cliffs produces bright NIR foam that is indistinguishable from surfable break foam at 10m resolution. During manual validation (March 26, 2026), Gaff Point was identified as the clearest example: it consistently shows 30%+ foam fraction, but the foam is from waves smashing against cliffs — not rideable breaking waves.

Other affected segments:
- **Gaff Point**: 31% foam = cliff interaction, not a surfable break
- **Western Head**: headland areas with cliff impact foam mixed with possible surf foam
- **Seaside**: outer coastal cliffs show foam but the sheltered lagoon does not
- Likely many more among the 16,939 scored segments that haven't been manually reviewed

Without coastline classification, the foam detection pipeline treats all foam equally, inflating scores for cliff-dominated segments.

## Data Sources

### Option A (Recommended): Nova Scotia LiDAR DEM

Nova Scotia has provincial LiDAR coverage for much of the coast through the NS GeoNOVA portal.

- **Resolution**: 1-2m (excellent for cliff detection)
- **Coverage**: Partial — urban areas and some rural coastline. May not cover all segments.
- **Format**: GeoTIFF or LAS point cloud
- **Access**: Free download from GeoNOVA (`https://nsgi.novascotia.ca/gdd/`)
- **CRS**: NAD83 CSRS / UTM Zone 20N (EPSG:2961)

### Option B: SRTM (Shuttle Radar Topography Mission)

- **Resolution**: 30m (coarser, but global coverage)
- **Coverage**: Complete for NS coast
- **Access**: Available in GEE as `USGS/SRTMGL1_003`
- **Limitation**: 30m may not resolve narrow cliff faces — a 10m cliff edge could be averaged with adjacent beach

### Option C: GEBCO (General Bathymetric Chart of the Oceans)

- **Resolution**: ~450m (15 arc-second grid)
- **Coverage**: Global, includes both land elevation and seafloor depth
- **Limitation**: Far too coarse for cliff detection, but useful for bathymetry integration (separate spec)

### Option D: Copernicus DEM (GLO-30)

- **Resolution**: 30m
- **Coverage**: Global
- **Access**: Available in GEE as `COPERNICUS/DEM/GLO30`
- **Advantage**: Same platform as Sentinel-2, easy to integrate in GEE pipeline

**Recommendation**: Use Copernicus DEM (GEE-native, 30m, global) as the primary source. Supplement with NS LiDAR where available for higher accuracy.

## Coastline Classification

### Classification categories

| Type | Slope | Elevation | Surfability | Foam Weight |
|------|-------|-----------|-------------|-------------|
| Sandy beach | < 5° | < 5m | High | 1.0 (full weight) |
| Gravel/cobble beach | 5-15° | < 10m | Medium | 0.8 |
| Rocky shore | 15-30° | 5-20m | Low-Medium | 0.5 |
| Low cliff | 30-60° | 10-30m | Very Low | 0.2 |
| High cliff | > 60° | > 30m | None | 0.05 |
| Headland tip | Variable | Variable | Medium (point break) | 0.6 |

### Classification method

For each coastline segment (500m):

1. **Extract elevation profile**: Sample DEM pixels in a 100m-wide strip landward of the coastline
2. **Compute slope**: Maximum slope in the strip perpendicular to the coastline
3. **Compute elevation**: Maximum and mean elevation within 50m of shore
4. **Classify**: Apply thresholds from the table above

```python
def classify_coast(max_slope_deg, max_elevation_m, mean_elevation_m):
    if max_slope_deg > 60 and max_elevation_m > 30:
        return "high_cliff", 0.05
    elif max_slope_deg > 30 and max_elevation_m > 10:
        return "low_cliff", 0.2
    elif max_slope_deg > 15:
        return "rocky_shore", 0.5
    elif max_slope_deg > 5:
        return "gravel_beach", 0.8
    else:
        return "sandy_beach", 1.0
```

### Headland detection

Headlands are special — they can host point breaks even with moderate elevation. Detect headlands by:
- Segment protrudes seaward relative to neighbors (convex coastline geometry)
- Already partially captured by the "coastal complexity" component in geometry scoring
- If a segment is classified as a headland AND has cliff-like elevation, use a moderate foam weight (0.6) rather than the cliff penalty

## Integration with Foam Detection

### Approach: Post-processing weight

Do NOT modify the foam detection pipeline (script 13) itself. Instead, apply coast-type weights as a post-processing step when computing composite scores.

```python
# In unified ranking (script 19) or new script
adjusted_foam_fraction = raw_foam_fraction * coast_type_weight

# Example:
# Gaff Point: raw foam 0.31, coast_type = "low_cliff", weight = 0.2
# Adjusted: 0.31 * 0.2 = 0.062 — drops from "active breaking" to "minimal"

# Lawrencetown: raw foam 0.45, coast_type = "sandy_beach", weight = 1.0
# Adjusted: 0.45 * 1.0 = 0.45 — unchanged
```

This preserves the raw data for analysis while correcting the scoring.

### Alternative: Binary filter

Instead of weighting, simply exclude cliff segments from foam analysis entirely. Simpler but loses information — some headland segments may have both cliff foam and real surf.

**Recommendation**: Use weighting, not binary exclusion. The headland case is too common and important.

## Spots This Would Help Most

Based on manual validation (PRD-v2-pipeline.md):

| Spot | Current Issue | Expected Fix |
|------|--------------|--------------|
| Gaff Point | 31% foam = cliff interaction | Drops to ~6% adjusted, correctly flagged as non-surf |
| Western Head | Mixed cliff + possible surf | Cliff portions weighted down, any real surf signal preserved |
| Seaside | Outer cliffs show false foam | Cliff segments deprioritized, lagoon mouth segments unaffected |
| Ingonish | Cape Breton headland, likely cliff foam | Would be correctly weighted |

Across all 16,939 segments, rough estimate: ~20-30% are cliff or rocky shore. Applying foam weights would significantly clean up the false positive rate for any automated ranking.

## Pipeline Integration

### Option A: New script `25_classify_coast.py`

Standalone script that adds coast type classification to the segments GeoJSON.

```
Input:  pipeline/data/coastline/ns_scored_segments.geojson
        Copernicus DEM (via GEE)

Output: pipeline/data/coastline/ns_segments_classified.geojson
        (adds coast_type, coast_slope, coast_elevation, foam_weight properties)
```

**Implementation**:
1. Load segments
2. For each segment, compute a 100m landward buffer
3. Query DEM within the buffer (GEE server-side or downloaded tiles)
4. Compute max slope and elevation
5. Classify and assign foam weight
6. Write updated GeoJSON

### Option B: Update script 11 (geometry scoring)

Add coast type as a component of the geometry score itself. The currently-skipped bathymetry component (20pt) could be partially replaced with a "surfability" component that includes coast type.

**Recommendation**: Option A — keep it as a separate script for modularity. It runs once and enriches the segment data. The unified ranking script (19) then reads the classification.

### GEE implementation

```python
dem = ee.Image("COPERNICUS/DEM/GLO30")

# For each segment buffer:
elevation_stats = dem.reduceRegion(
    reducer=ee.Reducer.max().combine(ee.Reducer.mean()),
    geometry=landward_buffer,
    scale=30
)

slope = ee.Terrain.slope(dem)
slope_stats = slope.reduceRegion(
    reducer=ee.Reducer.max(),
    geometry=landward_buffer,
    scale=30
)
```

All server-side — no large downloads needed.

## Expected Impact on Foam Detection Accuracy

### Before cliff filter

- Known cliff segments (Gaff Point, etc.) rank in top 20% by foam fraction
- ~20-30% of high-foam segments are likely cliff foam false positives
- Automated ranking would recommend non-surfable cliff segments

### After cliff filter

- Cliff segments drop to bottom 50% after foam weight adjustment
- Sandy beach segments with genuine foam are unaffected
- Headland point breaks retain moderate scores
- Estimated false positive reduction: 40-60% for segments with foam > 0.2

### Validation

- Re-run `12_calibrate.py` with adjusted foam scores
- Known beach break spots (Lawrencetown, Martinique, Cow Bay) should maintain or improve rank
- Known cliff areas (Gaff Point) should drop significantly
- Known point breaks at headlands (Snapjaw, Western Head) should retain moderate scores

## Effort Estimate

| Task | Time |
|------|------|
| GEE DEM extraction for all segments | 2-3h |
| Classification logic | 1-2h |
| Script 25 implementation | 2-3h |
| Integration with unified ranking | 1h |
| Validation against known spots | 1-2h |
| **Total** | **7-11h** |

## Dependencies

- Segment data from `10_segment_coastline.py` (done)
- GEE access (done — same auth as existing pipeline)
- Copernicus DEM available in GEE (public dataset, no additional auth)
- Unified ranking spec (SPEC-unified-spot-ranking.md) for integration

## Open Questions

1. **Is 30m DEM resolution sufficient?** A 30m pixel may straddle a cliff edge and a beach at the base. Could lead to misclassification of narrow beaches backed by cliffs. NS LiDAR (1-2m) would be better but has partial coverage.
2. **How to handle mixed-type segments?** A 500m segment might be half beach, half cliff. Could sub-segment at 100m resolution for classification, then compute a weighted average foam weight.
3. **Headland detection accuracy**: The simple "convex coastline" heuristic may flag coves incorrectly. May need to combine with geometry scoring's coastal complexity component.
4. **Seasonal vegetation**: Cliff faces may have different reflectance in summer (vegetated) vs. winter (bare). Does this affect DEM-based classification? Probably not — DEM is elevation, not reflectance.
5. **Tidal cliffs**: Some low cliffs are only exposed at low tide. Classification based on DEM alone misses tidal dynamics. Likely an edge case not worth solving initially.
