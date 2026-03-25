# WaveScout — Tasks

> Source of truth for project status. Updated after every work session.
> Last updated: 2026-03-24 (Phase 1 GO decision)

## Phase 1: Feasibility Prototype ✅ MOSTLY DONE — awaiting imagery review

### Pipeline Scripts (all working)
- [x] `01_test_gee_access.py` — scene inventory for configured spots
- [x] `02_export_sample_images.py` — export Sentinel-2 scenes to Google Drive
- [x] `03_check_conditions.py` — Open-Meteo Marine + Weather API queries
- [x] `04_run_feasibility.py` — orchestrates 01+03 across all spots
- [x] `05_generate_review_sheet.py` — CSV review sheets for manual labeling
- [x] `_script_utils.py` — shared utils, GEE init, provenance manifests

### Configuration
- [x] `.env` with GEE_PROJECT=seotakeoff (configurable, gitignored)
- [x] `_script_utils.py` loads from .env via python-dotenv
- [x] 3 spot configs: lawrencetown-beach, cow-bay, martinique-beach

### Data Generated (2026-03-24)
- [x] Scene inventories: ~306 clear scenes per spot (28% clear-sky rate)
- [x] Conditions manifests: marine + weather data for all spots
- [x] 24 GeoTIFF exports (8 per spot, Aug-Sep 2025) → Google Drive `wavescout_samples/`
- [x] Review CSVs for all 3 spots
- [x] Combined feasibility run manifest

### Review Tools
- [x] `web/index.html` — static feasibility viewer (loads manifests, shows scenes + conditions)
- [x] `FEASIBILITY-STATUS.md` — documented findings, gaps, and risks

### Remaining for Phase 1
- [x] **Imagery review** — visible white water on big swell days (3.8m Nov 19 2023), absent on flat days (0.3m Aug 30 2024)
- [x] **GO decision** — ✅ GO (2026-03-25). NIR-based detection confirmed viable. Foam clearly visible at moderate swell (1.6-2.0m), absent on flat days. NIR >> RGB for contrast.
- [x] `06_generate_thumbnails.py` — true-color PNG generation from GEE (bypasses GeoTIFF viewing issues)
- [x] `07_generate_band_composites.py` — NIR, SWIR-NIR-G, NIR-R-G, NDWI composites for swell vs flat comparison
- [x] Fixed band type mismatch bug (SCL is Byte, spectral bands UInt16 — cast all to UInt16)
- [x] Swell/imagery cross-reference: 135 clear scenes matched to marine conditions data
- [x] 6-date comparison set reviewed: 3 swell days (1.6m, 2.0m, 3.8m) vs 3 flat days (0.3m, 0.3m, 0.4m)
- [ ] **Graham: Pin lesser-known South Shore NS spots with characteristics** (point/beach/reef, swell window, notes)

## Key Findings
- **1,098-1,100 total scenes per spot**, ~306 clear (<30% cloud)
- **Marine data gap pre-2019**: Open-Meteo marine archive starts ~2019; earlier scenes only have wind
- **NIR (B8) is the best band for foam detection** — water absorbs NIR (black), foam reflects (bright white). Far better than RGB.
- **Moderate swell (1.6-2.0m) shows clearest break patterns** — storm days (3.8m) are too blown out for discrete detection
- **Different spots need different swell thresholds** — must build swell-response profiles, not binary detection
- **All 3 spots share Sentinel-2 tile T20TMQ**: same-day cross-spot comparison possible

## Phase 2: Geometry + Conditions Forecast Model — IN PROGRESS
**Approach:** Conditions-based forecast (which spots work today?) with satellite validation
**Graham provides:** Spot locations, type (point/beach/reef/slab), dominant swell window, notes

### Coastline Analysis (2026-03-24) ✅ DONE
- [x] `10_segment_coastline.py` — NS coastline from OSM Overpass (tiled), 500m segments with 250m stride, exposure arc filter → 16,939 exposed segments from 51,076 raw
- [x] `11_score_geometry.py` — Scores segments 0-100 (swell exposure 40pts, coastal complexity 25pts, bathymetry 20pts skipped w/o GEBCO, road access 15pts). STRtree spatial indexing.
- [x] `12_calibrate.py` — Matches 14 known spots to nearest segments. Top known spots (Martinique, Lawrencetown, Point Michaud) rank 88-94th percentile. Strong validation.

### Remaining
- [ ] **Graham: Pin lesser-known South Shore NS spots with characteristics** (point/beach/reef, swell window, notes)
- [ ] Ingest Graham's spot pins into `ns_spots.geojson` with metadata
- [ ] Bathymetry profile where available (CHS nautical charts / GEBCO)
- [ ] Historical swell correlation: "how often does each spot get ideal conditions?"
- [ ] Satellite validation: confirm white water on days conditions predict surf
- [ ] Forecast engine: given today's swell forecast, rank which spots are firing
- [ ] Imagery classification: detect breaking waves presence/extent per spot
- [ ] Spot type detection from imagery patterns (point break = asymmetric foam line, beach break = uniform)

## Phase 2.5: NIR Foam Detection Pipeline — NEXT
**Goal:** Automated foam detection across full scene archive to build swell-response profiles per segment

- [ ] `13_detect_foam_nir.py` — threshold-based NIR foam detection in nearshore zone per coastline segment
  - Extract B8 values in a buffer zone (0-200m from coastline) per segment
  - Compute foam fraction (pixels above NIR threshold / total water pixels)
  - Output: segment_id, date, swell_height, foam_fraction, foam_extent_m
- [ ] Run across full Lawrencetown archive (306 clear scenes with post-2019 marine data)
- [ ] Build swell-response profiles per segment:
  - Turn-on threshold (min swell where foam appears)
  - Optimal range (swell size with max foam extent)
  - Blow-out point (where foam becomes uniform / indistinct)
- [ ] Cross-spot comparison: same dates across Lawrencetown, Cow Bay, Martinique
- [ ] Validate against 14 known spots — do profiles match expected behavior?
- [ ] Extend to full NS coastline (16,939 exposed segments from geometry scoring)
- [ ] Merge geometry scores + NIR evidence + conditions into unified spot ranking
- [ ] Generate `spots.geojson` output bundle for web viewer

## Phase 3: Static Web Viewer — not started
- [ ] Map view (Nova Scotia)
- [ ] Detail panel with score explanation
- [ ] Confirmed vs candidate styling

## Infra / Config
- GitHub: `gmann14/wavescout`
- GEE Project: `seotakeoff` (via .env)
- Python 3.12 venv
- 6 git commits total
- No web deployment yet (pipeline-only project for now)

## Blockers
1. **Waiting on Graham's spot pins** — South Shore NS locations with type/characteristics
2. No cloud Supabase yet — local dev only until free tier opens up
