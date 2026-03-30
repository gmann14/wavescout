# WaveScout

## What This Is
Surf discovery tool using satellite imagery (Sentinel-2), coastline geometry, and ocean conditions to find candidate surf zones in Nova Scotia. See `docs/SPEC.md` for full product spec.

## Current Status
- **Phase 1: Feasibility** ✅ PASSED — NIR-based foam detection confirmed viable
- **Phase 2: Geometry Scoring** ✅ DONE — 16,939 exposed segments scored, known spots rank 88-94th percentile
- **Phase 2.5: NIR Foam Detection** ✅ DONE — 16,898 detections across 20 spots
- **Phase 2.7: Coastline Atlas** ✅ DONE — 2,839 sections tiled, atlas browser at /atlas
- **Phase 3: Static Web Viewer** ✅ BUILT — Next.js app in web/ (/, /atlas, /compare, /methodology, /about)
- **Phase 3.5: Unified Ranking** ✅ DONE — composite scoring (geometry + foam + profile), 374 segments with foam data

## Tech Stack
- Python 3.12 + venv
- Google Earth Engine (GEE) via `earthengine-api`
- Open-Meteo Marine + Weather APIs
- PIL/numpy for image processing
- Next.js 15 + Mapbox GL + Recharts (web viewer in web/)

## Key Technical Findings
- **NIR (B8) is the best band for foam detection** — water absorbs (black), foam reflects (bright white)
- **Moderate swell (1.6-2.0m) shows clearest break patterns** — storm days are too blown out
- **Different spots have different swell thresholds** — must build swell-response profiles per segment
- **10m resolution can detect foam presence and extent** but not individual wave shapes
- **All 3 test spots share Sentinel-2 tile T20TMQ** — same-day cross-spot comparison possible
- **Open-Meteo swell data starts 2021-10** for NS coast; earlier scenes have null swell values

## Project Structure
```
pipeline/
  configs/          — spot config JSON files (bbox, coordinates)
  scripts/          — numbered pipeline scripts (01-20)
  data/
    manifests/      — scene inventories, conditions, export manifests
    reviews/        — CSV review sheets for manual labeling
    thumbnails/     — generated PNG thumbnails (RGB + band composites)
    coastline/      — cached OSM coastline data
    known_spots/    — known NS surf spots
    gallery/        — spot gallery images (RGB + NIR thumbnails)
    atlas/          — coastline atlas sections + images
    calibration_report.json
    ns_known_spots.geojson
docs/
  SPEC.md           — full product spec
web/                — Phase 3 Next.js web viewer (pnpm)
  src/app/          — Next.js App Router pages (/, /atlas, /compare, /methodology, /about)
  src/components/   — React components (MapView, SpotPanel, SwellChart, etc.)
  public/data/      — optimized static data (built by build_web_data.py)
  public/gallery/   — satellite thumbnails (gitignored, regenerate with build_web_data.py)
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
13. `13_detect_foam_nir.py` — NIR foam detection per segment per scene (GEE server-side)
14. `14_build_swell_profiles.py` — swell-response profiles from foam detections
15. `15_generate_gallery_images.py` — satellite gallery thumbnails (RGB + NIR)
16. `16_generate_gallery_fast.py` — v2 gallery (12 swell bins, QS≥90, tide/direction metadata)
17. `17_tile_coastline.py` — tile NS coastline into ~3km atlas sections
18. `18_generate_atlas_fast.py` — atlas section gallery images across swell conditions
19. `19_annotate_gallery.py` — Pillow-based break pin annotations on gallery images
20. `20_rank_segments.py` — unified composite scoring (geometry + foam + profile)
- `build_web_data.py` — builds optimized static data for web viewer
- `build_atlas_web_data.py` — builds atlas static data for web viewer

## Commands
```bash
# Pipeline
source venv/bin/activate
python3 pipeline/scripts/<script>.py [args]

# Web viewer
cd web && pnpm dev    # dev server at localhost:3000
cd web && pnpm build  # production build
python3 pipeline/scripts/build_web_data.py  # rebuild web data from pipeline
```

## Environment
- `.env` with GEE_PROJECT=seotakeoff
- GEE auth via `earthengine authenticate`
- `web/.env.local` with NEXT_PUBLIC_MAPBOX_TOKEN (for map)

## Conventions
- All scripts write provenance manifests
- Numbered sequentially (01, 02, ...) for execution order
- Use `_script_utils.py` for shared utilities
- Cache downloaded data (coastline, roads) locally
- `.gitignore` excludes large cached data
