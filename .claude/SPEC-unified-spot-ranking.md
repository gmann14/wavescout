# Spec: Unified Spot Ranking

> Merge geometry scores, NIR foam evidence, and swell-response profiles into a single composite score per coastline segment.

## Problem

Currently, segment quality is spread across three independent data sources:

1. **Geometry score** (script 11) — 0-100 based on swell exposure, coastal complexity, road access, and bathymetry (skipped). Available for all 16,939 exposed segments.
2. **Foam detection stats** (script 13) — foam fraction, extent, NIR values per scene per segment. Available for ~31 spots (16,898 detections across configured spots only).
3. **Swell-response profiles** (script 14) — turn-on threshold, optimal range, blow-out point, primary direction. Derived from foam detections.

There is no single ranking that combines these signals. The web viewer color-codes segments by geometry score alone, which misses the satellite evidence entirely. A segment with mediocre geometry but consistent foam under swell is likely a real break — and should rank higher than a geometrically perfect segment that never shows foam.

## Approach

Build a composite score (0-100) for each segment that weights all available evidence. Segments with more data sources contributing get higher confidence, not necessarily higher scores.

### Scoring Formula

```
composite_score = geometry_weight * geometry_component
               + foam_weight     * foam_component
               + profile_weight  * profile_component

confidence = count of non-null components (1-3)
```

#### Component Weights

| Component | Weight | Max Points | Rationale |
|-----------|--------|------------|-----------|
| Geometry | 0.35 | 35 | Foundational — available everywhere, good baseline signal |
| Foam Evidence | 0.40 | 40 | Strongest signal — satellite-verified breaking waves |
| Swell Profile | 0.25 | 25 | Consistency bonus — segments that respond predictably to swell |

When fewer than 3 components are available, redistribute weights proportionally among available components so the score still fills 0-100.

#### Geometry Component (0-35)

Direct scaling of the existing geometry score:

```python
geometry_component = (geometry_score / 100) * 35
```

Already computed by script 11. Sub-components: swell exposure (40pt), coastal complexity (25pt), bathymetry (20pt, currently skipped), road access (15pt).

#### Foam Evidence Component (0-40)

Derived from foam detection stats across all observed scenes for the segment:

```python
# Filter to quality_score >= 60 scenes only
valid_obs = [d for d in detections if d['quality_score'] >= 60]

# Metrics
max_foam_fraction = max(d['foam_fraction'] for d in valid_obs)
mean_foam_fraction_swell = mean(d['foam_fraction'] for d in valid_obs if d['swell_height'] >= 1.0)
consistency = count(d for d in valid_obs if d['foam_fraction'] > 0.05) / len(valid_obs)
dynamic_range = max_foam_fraction - min_foam_fraction  # higher = more responsive

# Combine (each 0-1, weighted)
foam_raw = (
    0.35 * min(max_foam_fraction / 0.5, 1.0)       # caps at 50% max foam
  + 0.30 * min(mean_foam_fraction_swell / 0.3, 1.0) # caps at 30% mean under swell
  + 0.20 * consistency                                # how often it shows any foam
  + 0.15 * min(dynamic_range / 0.4, 1.0)             # responsive to conditions
)

foam_component = foam_raw * 40
```

#### Swell Profile Component (0-25)

Derived from the swell-response profile:

```python
# Does the segment have a clear turn-on threshold?
has_turnon = 1.0 if profile['turn_on_threshold'] is not None else 0.0

# Does it have an optimal range (not just noise)?
has_optimal = 1.0 if profile['optimal_range'] is not None else 0.0

# Does it respond to a specific direction (not omnidirectional noise)?
direction_specificity = profile['direction_concentration']  # 0-1, higher = more directional

# Observation depth — more scenes = more reliable profile
obs_depth = min(profile['observation_count'] / 30, 1.0)  # caps at 30 observations

profile_raw = (
    0.25 * has_turnon
  + 0.25 * has_optimal
  + 0.25 * direction_specificity
  + 0.25 * obs_depth
)

profile_component = profile_raw * 25
```

### Handling Missing Data

Most of the 16,939 segments have only geometry scores (foam detection has only been run for configured spots). The scoring must degrade gracefully:

| Data Available | Weight Redistribution | Confidence |
|----------------|----------------------|------------|
| Geometry + Foam + Profile | 35 / 40 / 25 (standard) | 3 (high) |
| Geometry + Foam (no profile) | 47 / 53 / 0 (proportional) | 2 (medium) |
| Geometry only | 100 / 0 / 0 (geometry fills 0-100) | 1 (low) |
| Foam only (no geometry — unlikely) | 0 / 100 / 0 | 1 (low) |

The confidence level (1-3) is displayed alongside the composite score in the web viewer so users understand how much evidence backs the ranking.

## Output Format

Updated `ns_scored_segments.geojson` or new `ns_ranked_segments.geojson` with additional properties per segment:

```json
{
  "type": "Feature",
  "properties": {
    "seg_id": "seg-04231",
    "geometry_score": 72,
    "composite_score": 68.4,
    "confidence": 3,
    "foam_component": 31.2,
    "geometry_component": 25.2,
    "profile_component": 12.0,
    "foam_obs_count": 45,
    "turn_on_threshold": 1.2,
    "optimal_swell": "1.5-2.0",
    "primary_direction": "SE",
    "rank": 142,
    "percentile": 99.2
  }
}
```

Also output a summary manifest:

```json
{
  "total_segments": 16939,
  "segments_with_foam": 487,
  "segments_with_profiles": 423,
  "score_distribution": {
    "p50": 34.2,
    "p75": 48.1,
    "p90": 62.3,
    "p95": 71.8,
    "p99": 84.2
  },
  "top_50": ["seg-04231", "seg-08812", "..."]
}
```

## Web Viewer Integration

### Color coding

Replace the current geometry-only color scheme with composite score colors:

| Score Range | Color | Label |
|-------------|-------|-------|
| 80-100 | Bright teal | Confirmed break |
| 60-79 | Orange | Strong candidate |
| 40-59 | Yellow | Moderate potential |
| 20-39 | Gray | Low signal |
| 0-19 | Dim gray | Minimal evidence |

### Confidence badge

Show confidence level on segment popups and spot panels:

- Confidence 3: "Satellite verified" (green badge)
- Confidence 2: "Partial data" (yellow badge)
- Confidence 1: "Geometry only" (gray badge)

### Sorting and filtering

- Default sort: composite score descending
- Filter by confidence level (show only satellite-verified segments)
- Filter by minimum composite score

## Pipeline Integration

### New script: `19_rank_segments.py`

```
Inputs:
  - pipeline/data/coastline/ns_scored_segments.geojson (geometry scores)
  - pipeline/data/manifests/*_foam_detections.json (all spots)
  - pipeline/data/manifests/*_swell_profiles.json (all spots)

Outputs:
  - pipeline/data/coastline/ns_ranked_segments.geojson
  - pipeline/data/manifests/unified_ranking_manifest.json

Process:
  1. Load geometry scores for all 16,939 segments
  2. Load foam detections, group by segment_id
  3. Load swell profiles, index by segment_id
  4. Compute composite score per segment
  5. Rank and assign percentiles
  6. Write output with provenance
```

### Update `build_web_data.py`

- Read unified ranking instead of raw geometry scores
- Include composite_score, confidence, and key profile metrics in web data
- Update `segments-high.json` threshold from geometry_score > 60 to composite_score > 50

## Edge Cases

1. **New spots added later**: Run foam detection for new spot, then re-run `19_rank_segments.py`. Script is idempotent — re-reads all available data.
2. **Segments at tile edges**: Some segments near Sentinel-2 tile boundaries have fewer valid observations (swath edge issues). Use `valid_pct` filter — segments with <80% valid pixels in most scenes get lower foam confidence.
3. **Cliff foam inflation**: Until the cliff foam filter (separate spec) is implemented, segments near known cliff areas (Gaff Point, etc.) may have inflated foam scores. Document this as a known limitation.
4. **Seasonal bias**: Winter scenes dominate highest-swell observations but also have snow contamination. Quality score filtering (QS >= 60) mitigates this, but note that foam_component may still be slightly inflated for some segments.
5. **Geometry score = 0 segments**: These were filtered out as unexposed — they should not receive composite scores at all. Skip them.

## Effort Estimate

| Task | Time |
|------|------|
| Script 19 implementation | 3-4h |
| Foam data aggregation logic | 2h |
| Profile metric extraction | 1h |
| build_web_data.py updates | 1-2h |
| Web viewer color/badge updates | 2-3h |
| Testing + validation against known spots | 2h |
| **Total** | **11-14h** |

## Dependencies

- Foam detections for all configured spots (done — 16,898 detections across 31 spots)
- Swell profiles (done for spots with foam data)
- Geometry scores (done — all 16,939 segments)
- To rank the full coastline by composite score, foam detection would need to run on all 16,939 segments (currently only ~31 configured spots). This is a separate, large GEE compute job.

## Open Questions

1. **Should the formula weights be tunable?** Could expose as CLI args to `19_rank_segments.py` for experimentation.
2. **Should we penalize segments that show foam on flat days?** High foam on low swell likely indicates contamination (sand, cliff). Could add a "false positive penalty" that subtracts points when foam_fraction > 0.2 on swell < 0.5m.
3. **How to handle the 16,000+ segments with no foam data?** They get confidence=1 and geometry-only scores. Is that useful enough to display, or should we hide them until foam data exists?
4. **Calibration**: Run the unified ranking against the 14 known spots from `12_calibrate.py`. Do they still rank in the 88-94th percentile? If composite score drops them, the weights need adjustment.
