# WaveScout

## What This Is
Surf discovery tool using satellite imagery (Sentinel-2), coastline geometry, and ocean conditions to find candidate surf zones in Nova Scotia. See `docs/SPEC.md` for full product spec.

## Current Status
- **Phase 1: Feasibility** ✅ PASSED — NIR-based foam detection confirmed viable
- **Phase 2: Geometry Scoring** ✅ DONE — 16,939 exposed segments scored, known spots rank 88-94th percentile
- **Phase 2.5: NIR Foam Detection** ← CURRENT PHASE
- **Phase 3: Static Web Viewer** — not started

## Tech Stack
- Python 3.12 + venv
- Google Earth Engine (GEE) via `earthengine-api`
- Open-Meteo Marine + Weather APIs
- PIL/numpy for image processing
- No web framework yet (pipeline-only)

## Key Technical Findings
- **NIR (B8) is the best band for foam detection** — water absorbs (black), foam reflects (bright white)
- **Moderate swell (1.6-2.0m) shows clearest break patterns** — storm days are too blown out
- **Different spots have different swell thresholds** — must build swell-response profiles per segment
- **10m resolution can detect foam presence and extent** but not individual wave shapes
- **All 3 test spots share Sentinel-2 tile T20TMQ** — same-day cross-spot comparison possible
- **Marine data only available from ~2019** via Open-Meteo; earlier scenes have wind only

## Project Structure
```
pipeline/
  configs/          — spot config JSON files (bbox, coordinates)
  scripts/          — numbered pipeline scripts (01-07 so far)
  data/
    manifests/      — scene inventories, conditions, export manifests
    reviews/        — CSV review sheets for manual labeling
    thumbnails/     — generated PNG thumbnails (RGB + band composites)
    coastline/      — cached OSM coastline data
    known_spots/    — known NS surf spots
    calibration_report.json
    ns_known_spots.geojson
docs/
  SPEC.md           — full product spec
web/
  index.html        — static feasibility viewer
research/           — background research docs
FEASIBILITY-STATUS.md — feasibility findings and GO decision
```

## Pipeline Scripts (run order)
1. `01_test_gee_access.py` — scene inventory
2. `02_export_sample_images.py` — export GeoTIFFs to Drive
3. `03_check_conditions.py` — Open-Meteo marine + weather
4. `04_run_feasibility.py` — orchestrate 01+03 across spots
5. `05_generate_review_sheet.py` — CSV review sheets
6. `06_generate_thumbnails.py` — true-color PNGs from GEE
7. `07_generate_band_composites.py` — NIR, SWIR, NDWI composites
8-9. Reserved
10. `10_segment_coastline.py` — OSM coastline → 500m segments with exposure filter
11. `11_score_geometry.py` — geometry scoring 0-100
12. `12_calibrate.py` — validate against 14 known spots

## Commands
```bash
source venv/bin/activate
python3 pipeline/scripts/<script>.py [args]
```

## Environment
- `.env` with GEE_PROJECT=seotakeoff
- GEE auth via `earthengine authenticate`

## Conventions
- All scripts write provenance manifests
- Numbered sequentially (01, 02, ...) for execution order
- Use `_script_utils.py` for shared utilities
- Cache downloaded data (coastline, roads) locally
- `.gitignore` excludes large cached data
