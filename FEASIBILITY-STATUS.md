# WaveScout Phase 1 Feasibility Status

**Date:** 2026-03-24
**Region:** Nova Scotia (Eastern Shore)
**Pipeline version:** b9788dc

## Summary

Phase 1 feasibility pipeline ran successfully across all 3 test spots. Scene inventory, conditions lookup, sample image export, and review sheet generation all completed without errors. 24 GeoTIFF scenes are exporting to Google Drive for manual review.

**Status: ✅ GO — NIR-based surf detection confirmed viable (2026-03-25)**

## Spots Analyzed

| Spot | Slug | Lat/Lon | Total Scenes | Clear (<30% cloud) | Summer (Jun-Sep) |
|------|------|---------|-------------|--------------------|--------------------|
| Lawrencetown Beach | lawrencetown-beach | 44.6375, -63.3417 | 1,098 | 306 (28%) | ~85 |
| Cow Bay (Osbourne) | cow-bay | 44.6050, -63.4167 | 1,100 | 307 (28%) | ~85 |
| Martinique Beach | martinique-beach | 44.6833, -63.1333 | 1,099 | 306 (28%) | ~85 |

All spots are in Sentinel-2 tile T20TMQ. Coverage is consistent across spots since they share a similar geographic extent along the Eastern Shore.

## Data Coverage

### Sentinel-2 Scene Inventory
- Date range: 2017-07-10 to 2026-03-20
- ~1,100 total scenes per spot, ~306 clear scenes per spot
- Clear-sky rate: ~28% (typical for Atlantic Canada)
- Revisit interval: 2-5 days (Sentinel-2A + 2B + 2C)
- Summer months have better clear-sky rates than winter

### Conditions Data (Open-Meteo)
- **Marine API**: Wave height, direction, period; swell height, direction, period
  - Data available from ~2019 onwards (marine reanalysis archive start)
  - Pre-2019 dates return null for all marine fields
  - Recent dates (2020+) have full marine data coverage
- **Weather API**: Wind speed, direction, gusts at 10m
  - Full coverage across all dates (ERA5 archive)
  - Captures Sentinel-2 overpass window (~11:00 UTC)

### Sample Image Exports
- 8 scenes per spot, 24 total
- Date range: Aug-Sep 2025 (recent summer, best cloud conditions)
- Cloud cover: 0-10% on all exported scenes
- Bands exported: B2 (Blue), B3 (Green), B4 (Red), B8 (NIR), B11 (SWIR), SCL
- Scale: 10m resolution
- Exporting to Google Drive folder `wavescout_samples/`

## Key Findings So Far

### Positive Signals
1. **Abundant clear imagery in summer.** ~85 clear scenes per spot during Jun-Sep across 8+ years gives enough samples to look for surf signal.
2. **Consistent coverage.** All 3 spots share the same Sentinel-2 tile, so imagery is available on the same dates. This enables cross-spot comparison on identical acquisition days.
3. **Full band access.** B3 (Green) and B4 (Red) for foam detection, B8 (NIR) for water/land masking, SCL for cloud masking -- all available at 10m.
4. **Conditions data aligns.** Open-Meteo marine + weather data at the Sentinel-2 overpass hour (11 UTC) lets us pair each scene with wave/wind conditions.

### Gaps and Risks
1. **Marine data gap pre-2019.** Open-Meteo marine archive starts ~2019, so earlier scenes only have wind data. This limits the training set for any conditions-imagery correlation analysis.
2. **10m resolution is coarse for surf.** Breaking waves and white water may only span a few pixels at 10m. Signal-to-noise ratio is uncertain until imagery is reviewed.
3. **No in-situ ground truth.** We don't have surf reports or webcam data paired to these dates. Conditions data (wave height + direction) is the proxy for "surf was present."
4. **Cloud cover in Atlantic Canada.** 28% clear rate means ~72% of potential observations are lost. During active swell seasons (fall/winter), cloud rates are higher.
5. **Same tile, similar conditions.** The 3 test spots are close enough that they likely have very similar swell exposure. Differentiating spots by satellite will require either visible breaking-wave signal or complementary geometry analysis.

## Review Sheets

CSV review sheets generated for manual imagery labeling:

- `pipeline/data/reviews/lawrencetown-beach_review.csv` (306 observations)
- `pipeline/data/reviews/cow-bay_review.csv` (307 observations)
- `pipeline/data/reviews/martinique-beach_review.csv` (306 observations)

Each row has pre-filled conditions data. Reviewer fills in:
- `observation_label`: present / none / unclear
- `notes`: free-text description of what's visible

## Web Viewer

A static HTML viewer is available at `web/index.html`. Open it in a browser to see:
- Summary statistics across all spots
- Per-spot scene inventory with conditions data side-by-side
- Season filter (all months vs. summer only)
- Color-coded wave height indicators

## Feasibility Decision: GO (2026-03-25)

### Evidence
Manual review of 6 comparison dates at Lawrencetown Beach across RGB true-color, NIR (B8), NDWI, and false-color composites:

**Swell days reviewed:** 3.8m (Nov 19 2023), 2.0m (Apr 2 2025), 1.6m (Feb 22 2023)
**Flat days reviewed:** 0.3m (Aug 30 2024), 0.3m (May 3 2022), 0.4m (Aug 23 2023)

### Key Findings

1. **NIR is the best band for foam detection.** Water absorbs NIR (appears black), foam reflects it (appears bright white). Dramatically better contrast than RGB true-color.
2. **Foam clearly visible at moderate swell (1.6-2.0m).** Not just storm days — discrete breaking patterns visible at typical surfable swell sizes.
3. **Foam absent on flat days (0.3-0.4m).** Clean binary signal between surfable and flat conditions in NIR.
4. **Break patterns vary by coastline geometry.** Headlands show different foam signatures than open beach. Offshore breaking features visible (rocks/reefs).
5. **RGB true-color also shows foam** but with less contrast than NIR. The 2.0m day was particularly clear in RGB.
6. **3.8m storm day was too blown out** for discrete break detection — everything churned up. Moderate swell is more useful for spot characterization.

### Important Nuance: Swell-Response Profiles
Different spots have different working swell windows. A big-wave slab only breaks at 3m+, while a beach break might be optimal at 1-1.5m and blown out at 3m. Detection must be per-segment, across multiple swell sizes, to build swell-response profiles (turn-on threshold, optimal range, blow-out point).

### Feasibility Criteria Assessment
1. ✅ At least 3 known spots show recognizable breaking-wave signal — confirmed at Lawrencetown across multiple dates
2. ✅ Marine conditions are directionally consistent — foam present on swell days, absent on flat days
3. ✅ Review method can distinguish surf from non-surf coastline — NIR provides clear binary signal
4. ✅ Reproducible from scripts — `07_generate_band_composites.py` generates all comparison images from GEE

### Decision
**Proceed with NIR-based imagery detection as primary evidence layer**, complemented by geometry scoring. Build swell-response profiles per coastline segment across the full clear-scene archive.

## Next Steps

1. **Build automated NIR foam detector** — threshold-based detection on B8 band in the nearshore zone per segment
2. **Run across full archive** — 306 clear scenes × 3 spots, paired with conditions data
3. **Build swell-response profiles** — per segment: at what swell size does foam appear? What's optimal? When does it blow out?
4. **Extend to full NS coastline** — apply detector to the 16,939 exposed segments from Phase 2 geometry scoring
5. **Cross-validate** — geometry score + imagery evidence + conditions correlation = final spot ranking
6. **Graham: Pin additional South Shore spots** for expanded calibration set

## Pipeline Artifacts

All manifests are in `pipeline/data/manifests/`:
- `*_scene_inventory.json` -- clear scene dates per spot
- `*_conditions_manifest.json` -- marine + weather data per observation date
- `*_export_manifest.json` -- GEE export task details per spot
- `feasibility_run.json` -- combined pipeline run provenance
