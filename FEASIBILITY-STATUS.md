# WaveScout Phase 1 Feasibility Status

**Date:** 2026-03-24
**Region:** Nova Scotia (Eastern Shore)
**Pipeline version:** b9788dc

## Summary

Phase 1 feasibility pipeline ran successfully across all 3 test spots. Scene inventory, conditions lookup, sample image export, and review sheet generation all completed without errors. 24 GeoTIFF scenes are exporting to Google Drive for manual review.

**Status: Awaiting imagery review to make go/no-go decision.**

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

## Next Steps

1. **Review exported imagery.** Download GeoTIFFs from Google Drive (`wavescout_samples/`). Open in QGIS or similar. Look for white water / foam signal in B3/B4 at known break zones.
2. **Label review sheets.** For each exported scene date, fill in `observation_label` and `notes` in the corresponding CSV.
3. **Assess signal.** If surf signal is visible in any scenes, correlate with conditions data. Are visible signals present when swell > 1m and period > 8s?
4. **Go/no-go decision.**
   - **Go:** If surf signal is visible and correlates with conditions, proceed to automated detection (spectral indices, ML).
   - **Pivot:** If signal is too faint at 10m, shift to geometry-first ranking using coastline orientation + bathymetry, with imagery as secondary validation.
   - **No-go:** If neither approach seems viable at 10m resolution, consider Sentinel-2 20m bands, commercial 3m imagery, or SAR-based approaches.

## Pipeline Artifacts

All manifests are in `pipeline/data/manifests/`:
- `*_scene_inventory.json` -- clear scene dates per spot
- `*_conditions_manifest.json` -- marine + weather data per observation date
- `*_export_manifest.json` -- GEE export task details per spot
- `feasibility_run.json` -- combined pipeline run provenance
