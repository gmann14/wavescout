# WaveScout v2 Pipeline — PRD

> Based on manual spot validation session (March 26, 2026).
> Graham reviewed 9 spots, identified 5 contamination sources, 6 coordinate errors, and critical gallery improvements.

---

## Problem Statement

The v1 pipeline produces foam detection data and gallery images with significant quality issues:
- **Contamination sources** inflate foam readings (clouds, snow, sand, cliffs, swath edges)
- **Gallery images** selected by swell height only, not by scene quality
- **Spot coordinates** wrong or imprecise for 6+ spots
- **Missing metadata** in gallery overlay (swell direction, period, data quality)
- **Tide data** was looked up at wrong time (fixed: 15:00 UTC, not 10:30 UTC)
- **No spot characteristic data** (break type, preferred direction, experience level)

## Goals

1. **Clean foam detection** — SCL-masked, snow-aware, cloud-filtered
2. **Smart gallery selection** — best images of spots actually working
3. **Accurate spot data** — correct coordinates, rich metadata from WannaSurf/Surfline
4. **Data quality transparency** — every scene has a quality score

---

## 1. SCL-Based Scene Quality Filtering

### Contamination Sources Identified

| Source | Impact | Example | Fix |
|--------|--------|---------|-----|
| Clouds | High NIR mimics foam | Hell Point 73% at 0.4m | SCL cloud mask (classes 8, 9, 10) |
| Snow on land | Bleeds into buffer | Cherry Hill 80% at 0.3m | SCL snow mask (class 11) on land pixels only |
| Swath edges | Black/nodata pixels | Hirtle's & Gaff Point 5/5 (2023-11-19) | Valid pixel threshold (<80% → skip) |
| Low-tide sand | Bright sand = false foam | Cherry Hill 64% at low tide | Dynamic water mask accounting for tidal sand |
| Cliff foam | Wave impact ≠ surfable break | Gaff Point 31% = cliff interaction | Coastline classification (DEM/slope) |

### Implementation

**Script: `13_detect_foam_nir.py` updates**
- Add SCL pixel classification before foam detection
- Calculate per-scene quality metrics:
  - `cloud_pct`: % of buffer zone classified as cloud (SCL 8, 9, 10)
  - `snow_pct`: % of land within AOI classified as snow (SCL 11)
  - `valid_pct`: % of pixels with actual data (vs nodata/swath edge)
  - `quality_score`: composite 0-100 (weighted: cloud 50%, valid 30%, snow 20%)
- **Only count foam on water pixels** (SCL class 6) — this preserves winter scenes with snow on land
- Store quality metrics in foam detection manifest

**Scene filtering thresholds:**
- `quality_score >= 60` → usable for analysis
- `quality_score >= 80` → high quality (preferred for gallery)
- `quality_score < 40` → discard from foam statistics

### Snow Handling (Graham's insight)
Snow on land is okay — we just ignore white on land pixels by masking SCL class 11 within the buffer zone. Only water-classified pixels contribute to foam fraction. This preserves winter ocean data while eliminating land contamination.

---

## 2. Smart Gallery Image Selection

### Current Approach (v1)
- Pick 5 scenes at different swell bins (flat/small/moderate/big/storm)
- Select highest foam fraction per bin
- No quality filtering

### v2 Approach
Per spot, select scenes that tell the story:

1. **Baseline scene** — flat day (swell < 0.5m), quality_score >= 80. Shows the spot at rest.
2. **Turn-on scene** — swell near the spot's activation threshold, quality_score >= 70. First sign of breaking.
3. **Optimal scene** — ideal swell height + preferred direction + period 7s+, quality_score >= 80. The spot at its best.
4. **Big day scene** — large swell showing the spot maxed out or blowing out.
5. **Tidal comparison** — same-ish swell at different tide states (if spot is tide-dependent).

### Selection priority:
```
clean_scenes = scenes WHERE quality_score >= 70
                       AND valid_pct >= 0.8
                       ORDER BY quality_score DESC

# For optimal: also filter by preferred swell direction ± 30°
# For tidal: pick two scenes at similar swell but different tide_state
```

### Output resolution
- **Adaptive image size** based on bbox area:
  - bbox area < 0.002 → 800px wide
  - bbox area 0.002-0.003 → 1000px wide
  - bbox area > 0.003 → 1200-1600px wide
- Goal: consistent meters-per-pixel across all spots

---

## 3. Coordinate & Metadata Corrections

### Spots needing coordinate fixes (6)

| Spot | Issue | Fix Source |
|------|-------|-----------|
| Summerville Beach | Wrong location entirely | WannaSurf + Google Maps |
| Western Head | Off the actual headland | WannaSurf + Surfline |
| White Point Beach | Slightly off | WannaSurf (43.9618, -64.7353) |
| Broad Cove | ~100km wrong (Musquodoboit vs south shore) | Surfline shows near Cherry Hill (~44.07, -64.56) |
| Lawrencetown | Needs repositioning | WannaSurf (44.6422, -63.3420) + bbox tighten |
| Martinique Beach | Pin on lagoon side, should be ocean | Google Maps + satellite |

### Bbox adjustments needed

| Spot | Current | Issue | Target |
|------|---------|-------|--------|
| Lawrencetown | 0.10 × 0.04 | Way too wide, images tiny | 0.05 × 0.03 |
| White Point | 0.07 × 0.05 | Too wide | 0.05 × 0.04 |
| Martinique | 0.07 × 0.04 | Slightly wide | 0.05 × 0.04 |

### WannaSurf scraping task
Scrape all 39 NS spot pages on WannaSurf for:
- Break type (beach-break, point-break, reef-rocky, rivermouth, sand-bar)
- Direction (right, left, both)
- Quality rating (1-5 stars)
- Frequency (how often it works)
- Experience level (all / experienced / pros)
- Precise lat/lng from detail page
- Any text descriptions

Also cross-reference with Surfline spot coordinates where available.

---

## 4. Gallery Overlay Improvements

### Current overlay info
- Date, swell height, foam %, tide (height + state), RGB/NIR toggle

### Add to overlay
- **Swell direction** (degrees + compass, e.g., "161° SSE")
- **Swell period** (seconds, e.g., "11.1s")
- **Data quality indicator** (green/yellow/red dot, or quality_score %)
- **Break type** (from WannaSurf data, e.g., "Beach Break — Left & Right")

### Exact acquisition timestamps
- Extract `system:time_start` from GEE during gallery generation
- Use exact timestamp for tide lookup (instead of estimated 15:00 UTC)
- Display actual time on overlay (e.g., "2023-09-05 14:47 UTC")

---

## 5. Spot-Specific Swell Profiles (from validation)

| Spot | Type | Activation | Preferred Dir | Period | Tide | Notes |
|------|------|------------|---------------|--------|------|-------|
| Snapjaw | Point | 3.4m+ | ESE? | — | Not dependent | Cloud false positives, subtle foam |
| Hell Point | Beach/headland | 1.7m? | 118° SE | 9.3s+ | Unknown | Cloud issues, SSW doesn't work |
| Hirtle's | Beach | 1.0m? | SE 100-110° | 7s+ | Works at high | A-frames at 1.7m, snow contamination |
| Gaff Point | Headland/uncertain | Unknown | Maybe S/SSW? | — | — | Mostly cliff foam, uncertain break |
| Cherry Hill | Beach | 1.4m? | SE 100-140° | 8s+ | Mid preferred? | No A-frames on E swell; possible RH point on SW headland |
| Seaside | Coastal/sheltered | 3.0m+ | SSE 161° | 11s+ | — | Lagoon shelters, outer coast only |
| Lawrencetown | Beach complex | 1.0m+ | Various | — | — | Multiple zones, lower threshold than south shore |
| Cow Bay | Cove | 2.0m+ | SSE 170°+ | 9s+ | — | Cove geometry focuses swell, wedge at headland junction |

---

## 6. Algorithm Improvements (future phases)

### Cliff Foam Filter
- Use DEM/slope data to classify coastline type (beach vs cliff vs headland)
- Weight foam differently: beach foam = surfable, cliff foam = impact only
- Could use OSM coastline tags or Nova Scotia GIS data

### Exposure Classification
- Fully exposed (open beach facing dominant swell)
- Partially sheltered (cove, bay)
- Harbour/lagoon (needs huge swell to activate)
- Factor into scoring thresholds

### Multi-Zone Beach Detection
- Long beaches like Lawrencetown are multiple spots
- Different sections respond differently to same swell
- Consider sub-spot segmentation for barrier beaches

### Swell Window Scoring
- Per-spot preferred swell direction ± acceptable range
- Foam fraction weighted by swell direction match
- "This spot works 30% of days" type stat

---

## Implementation Order

1. **WannaSurf scrape** — get rich spot metadata, fix coordinates (1-2 hours)
2. **SCL masking in foam detection** — update script 13 (2-3 hours, GEE compute)
3. **Reprocess all spots** with SCL masking (overnight agent run)
4. **Gallery v2 selection** — update script 15 with quality filtering + smart selection (2-3 hours)
5. **Gallery v2 regeneration** — exact timestamps, adaptive resolution, quality overlay (overnight)
6. **Web viewer updates** — direction/period in overlay, quality indicator, corrected coordinates (1-2 hours)
7. **Cliff foam filter** — DEM integration (Phase 4, lower priority)

---

## Validation Evidence

Full validation log with per-spot observations: `docs/SPOT-VALIDATION-LOG.md`

Spots reviewed (March 26, 2026):
1. Snapjaw — cloud false positives, high activation threshold, point break signature
2. Hell Point — cloud contamination, SE swell shows promise
3. Hirtle's Beach — snow contamination, A-frames visible on clean scenes, swath edge
4. Gaff Point — cliff foam dominates, uncertain break, swath edge
5. Cherry Hill — snow worst offender, possible RH point break discovery, swell direction matters
6. Seaside — 100% cloud false positive, sheltered by lagoon, needs 3m+ SSE
7. Lawrencetown — bbox too wide, lower activation threshold, multiple break zones
8. Cow Bay — snow contamination, cove geometry, SSE swell works
9. Martinique — pin on wrong side of beach, cloud issues

---

*Written March 26, 2026 by Alfred based on Graham's manual validation session.*

---

## v2.5 Updates (2026-03-27)

### Gallery Expansion — COMPLETE
- **12 swell bins** (was 5): glass, flat, small-, small, small+, moderate, moderate+, big, big+, storm, storm+, xxl
- **QS threshold lowered to 90** (was 95): captures high-energy scenes with slight cloud cover
- **Winter scenes included**: Removed Dec-Mar exclusion + snow_land_pct filter. Best swell comes in winter; human can visually distinguish foam from snow at 10m.
- **CHS tide integration**: predicted tide at Sentinel-2 overpass time (~15:00 UTC) per scene
- **Swell direction + period**: metadata per scene, shown in UI lightbox and cards
- **Result**: 31 spots, 248 scenes, 436 images (up from 19 spots, ~85 scenes)

### Spot Data Corrections
- Cow Bay → The Moose (matches Surfline naming, same coords)
- Forevers removed (possibly mythical)
- Broad Cove area 3 spots confirmed with precise coords

### Product Direction Pivot
Graham identified fundamental limitation: foam % alone cannot reliably distinguish foam/snow/cloud at 10m for automated spot discovery. 

**New strategy: Visual Atlas → Algorithm Experiments**
1. Tile entire NS coastline (~1000km+, ~300-400 sections at ~3km)
2. Pull 10-15 scenes per section across swell height/direction/period
3. Build browsable viewer for manual spot discovery
4. Use human labels as ground truth for algorithm development
5. Multi-layer scoring: temporal stacking + swell-direction response + spatial patterns + geometry

The atlas itself has standalone value as a comprehensive visual record of NS coast conditions.
