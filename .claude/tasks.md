# WaveScout — Tasks

> Source of truth for project status. Updated after every work session.
> Last updated: 2026-03-30 (break pins, atlas labeling, compare view, unified ranking, 5 specs)

## Phase 1: Feasibility Prototype ✅ COMPLETE — GO decision made

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
- **Marine swell data starts 2021-10**: Open-Meteo swell data for NS begins Oct 2021; earlier scenes have null swell values
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
- [x] **Graham pinned 6 South Shore spots** — Snapjaw, Rafuse Island, Hell Point, Hirtle's Beach, Gaff Point, Seaside
- [x] Ingested into `ns_spots.geojson` — 20 total spots (9 Graham + 11 public sources)
- [x] Created configs for all 20 spots with correct bboxes and verified segment coverage
- [ ] Bathymetry profile where available (CHS nautical charts / GEBCO)
- [ ] Historical swell correlation: "how often does each spot get ideal conditions?"
- [ ] Satellite validation: confirm white water on days conditions predict surf
- [ ] Forecast engine: given today's swell forecast, rank which spots are firing
- [ ] Imagery classification: detect breaking waves presence/extent per spot
- [ ] Spot type detection from imagery patterns (point break = asymmetric foam line, beach break = uniform)

## Phase 2.5: NIR Foam Detection Pipeline — IN PROGRESS
**Goal:** Automated foam detection across full scene archive to build swell-response profiles per segment

### Scripts Built (2026-03-25)
- [x] `13_detect_foam_nir.py` — NIR foam detection in nearshore buffer zone per coastline segment
  - GEE server-side computation (reduceRegion) — no imagery downloads
  - Extracts B8 values in 0-200m seaward buffer per segment
  - SCL water mask (class 6) filters land/cloud pixels
  - Foam fraction, foam extent, mean/max NIR per segment per scene
  - Pairs each observation with Open-Meteo marine conditions
  - Tested: 10 scenes × 23 segments = 213 detections, 0 errors
- [x] `14_build_swell_profiles.py` — swell-response profiles per segment
  - turn_on_threshold: min swell where foam_fraction > 0.05
  - optimal_range: swell bin with highest mean foam_fraction
  - blow_out_point: swell where foam_fraction > 0.80
  - primary_direction: swell direction producing most foam
  - Bins by swell height (0.5m bins) and direction (8 compass sectors)
  - Tested: 23 complete profiles from 10-scene Lawrencetown sample

### Key Technical Discovery
- **Open-Meteo swell data starts 2021-10** for NS (not 2019 as previously assumed)
  - Dates before Oct 2021 return null for swell_wave_height
  - 120 clear scenes available post-2021-10 for Lawrencetown (<15% cloud)
  - MIN_DATE set to 2021-10-01 in script 13

### Validation Results (10-scene sample)
- Foam fraction ranges 0.0-0.93 — excellent dynamic range
- Swell 0.28m → foam 0.02-0.15 (low/none) ✅
- Swell 0.88-0.92m → foam 0.30-0.67 (active breaking) ✅
- Profiles: turn-on at 0.28-0.42m, optimal 0.5-1.0m, directional from S/SE/E ✅

### v2 Pipeline Updates (2026-03-26) ✅ DONE
- [x] **SCL quality metrics** added to `13_detect_foam_nir.py`:
  - `cloud_pct`, `shadow_pct`, `snow_land_pct`, `valid_pct`, `quality_score` per scene
  - Quality score: cloud 40% + valid 30% + snow 20% + shadow 10% (0-100)
  - Metrics attached to every detection record for easy filtering
  - `scene_quality` array in manifest + quality summary in `summary.quality`
  - Thresholds: discard <40, usable >=60, high >=80
- [x] **Overpass time fix**: Open-Meteo index corrected from 11 → 15 UTC (NS overpass is ~15:00 UTC / 11 AM AST)
- [x] **`--all-spots` flag**: processes all configs in `pipeline/configs/` sequentially with summary table
- [x] **22 new spot configs** generated (42 total: 20 existing + 22 new):
  - Tier 1 (foam-verified): lawrencetown-point, left-point, right-point, the-cove, minutes, osbourne
  - Tier 2 (WannaSurf/Surfline): andrews-head, blueberry-bay, eastern-brook, fishermans-reserve, forevers, juicys, killaz, meadows-point, point-pleasant-beach-park, pubnico-beach, rissers, rudys, sable-island, seals, the-juice, the-meadows
- [x] Verified: `--help` parses correctly, `--limit 3` test produces quality metrics in manifest (qs=99.9 for Lawrencetown clear days)

### Remaining
- [x] Run full Lawrencetown archive — **DONE** (120 scenes, 2,708 detections, 23 profiles)
- [x] Run all other spots — **16/20 DONE** (agent completed overnight Mar 25-26)
  - ✅ lawrencetown-beach: 2,708 | ✅ clam-harbour: 3,112 | ✅ martinique-beach: 1,408
  - ✅ cow-bay: 1,306 | ✅ kennington-cove: 1,196 | ✅ point-michaud: 1,146
  - ✅ white-point: 1,026 | ✅ hirtles-beach: 767 | ✅ rafuse-island: 741
  - ✅ snapjaw: 738 | ✅ summerville: 739 | ✅ cherry-hill: 711
  - ✅ seaside: 582 | ✅ gaff-point: 528 | ✅ hell-point: 166 | ✅ western-head: 124
  - Total: 16,898 foam detections across 16 spots
- [x] Run remaining foam spots: broad-cove, gullivers-cove, ingonish ran during gallery generation (19 total spots now)
- [x] `15_generate_gallery_images.py` — gallery thumbnails for web viewer
  - **v2 (2026-03-27):** 12 swell bins (glass→xxl), QS≥90, winter scenes included
  - Picks best scene per swell bin (highest foam fraction + quality score)
  - Generates RGB + NIR thumbnails (800px fixed width) via GEE
  - CHS tide API integration: tide_m + tide_state per scene at overpass time (~15:00 UTC)
  - Swell direction + period metadata per scene
  - **436 images across 31 spots** (248 scenes), manifest at pipeline/data/gallery/manifest.json
  - Top spots: Clam Harbour 11 scenes (0.3→4.3m), 10 spots with 10 scenes each
  - Winter scenes included (best swell = winter storms, human can distinguish foam from snow)
- [ ] Cross-spot comparison: same dates across all spots
- [ ] Validate profiles against known spot behavior
- [ ] Extend to full NS coastline (16,939 exposed segments from geometry scoring)
- [ ] Merge geometry scores + NIR evidence + conditions into unified spot ranking
- [ ] Generate `spots.geojson` output bundle for web viewer

## Phase 2.7: Coastline Visual Atlas — ✅ COMPLETE (2026-03-28)
**Goal:** Comprehensive visual atlas of entire surfable NS coastline for manual spot discovery
**Result:** 2,839 sections tiled (~3km each), atlas browser UI at `/atlas`

### What was built
- [x] `17_tile_coastline.py` — tiles NS coastline into ~3km sections (2,839 sections, 16,605 segments covered)
- [x] `18_generate_atlas_fast.py` — generates gallery images for atlas sections across swell conditions
- [x] `build_atlas_web_data.py` — builds atlas static data for web viewer
- [x] `AtlasMap.tsx` + `AtlasSectionPanel.tsx` — atlas browser UI with map navigation
- [x] `/atlas` page in Next.js app — functional coastline browser

### Key Decisions (2026-03-27)
- NS surfable coastline is 1000km+ (not 200-300km as initially estimated)
- Manual human verification at 10m/pixel IS viable — Graham can identify breaks at this resolution
- Foam % alone insufficient for automated spot discovery (can't distinguish snow/cloud/foam reliably)
- **Phase 1 = browsable atlas** (manual discovery tool), **Phase 2 = algorithm experiments** with human labels as ground truth

### Remaining
- [x] Labeling UI: "Flag potential break" button with coordinate picker + notes
- [x] Export flagged locations as JSON with section metadata
- [ ] Full coast image coverage (many sections may still lack gallery images)
- [ ] Progressive loading for large atlas datasets

## Phase 3: Web Viewer ✅ BUILT
- [x] Next.js 15 app in `web/` — App Router, TypeScript, Tailwind CSS, Mapbox GL
- [x] **Map page** — full-screen dark Mapbox map centered on NS coast
  - Three-tier markers: verified spots (20, teal pins), high-scoring candidates (2,420 >60, orange dots), all scored segments (6,650 >40, gray dots visible on zoom)
  - Color-coded by score, clustered at zoom, labels for verified spots
  - Segment hover popups (ID, score, rank)
- [x] **Spot detail panel** — slide-up mobile, sidebar desktop
  - Spot metadata (name, type, source, confidence badge)
  - Foam detection stats (total observations, satellite passes)
  - Swell response profile chart (Recharts bar chart: foam% vs swell bins)
  - Turn-on threshold, optimal range, blow-out point metrics
  - Satellite image gallery with RGB/NIR toggle, swell height + foam score overlay
- [x] **Methodology page** (`/methodology`) — renders docs/METHODOLOGY.md with styled markdown
- [x] **About page** (`/about`) — project info, pipeline steps, data sources, credits
- [x] `pipeline/scripts/build_web_data.py` — builds optimized static data from pipeline outputs
  - spots.json (10KB), segments-high.json (607KB), segments-all.json (856KB)
  - Per-spot detail files with aggregated swell profiles
  - Gallery manifest + image copying
- [x] Dark ocean theme (navy/teal/orange), mobile-first responsive
- [x] Build passes clean (`pnpm build`)
- [ ] **Mapbox token needed** — set NEXT_PUBLIC_MAPBOX_TOKEN in web/.env.local
- [x] **ImageGallery.tsx** updated — cards show swell direction label, period, tide state emoji + level
- [x] **Lightbox overlay** shows swell direction + period (e.g. "2.1m SSW @ 8s")
- [x] Cross-spot same-date comparison view — `/compare` page with swell/spot filters
- [x] Break pin annotations on gallery images — `19_annotate_gallery.py` + Breaks toggle in UI
- [ ] Algorithm Experiments page
- [x] Coastline atlas browser (section-based navigation) — `/atlas` page

## Infra / Config
- GitHub: `gmann14/wavescout`
- GEE Project: `seotakeoff` (via .env)
- Python 3.12 venv
- 20+ git commits (as of Mar 30)
- No web deployment yet (pipeline-only project for now)

## Spot Data Changes (2026-03-27)
- **Cow Bay → The Moose**: Renamed to match Surfline (same coords 44.61383, -63.43175). "Cow Bay" kept as alias. Surfline ID `584204204e65fad6a77094cb`.
- **Forevers removed** from spots.json (42→41 spots). Flagged as possibly mythical.
- **3 Cow Bay area breaks confirmed**: The Moose (reef), Osbourne (point, 44.61774, -63.417031), Minutes (44.632158, -63.415339)
- **Broad Cove area coords confirmed**: Broad Cove (44.17665, -64.47789), Artie's (44.16778, -64.47716), Bullfield (44.17041, -64.47671)

## Spot Finder — Honest Assessment (2026-03-27)

### What Sentinel-2 (10m/pixel) CAN do:
- Coastline-scale energy monitoring (more white along shore = more energy)
- Confirm known spots active on a given day
- Condition visualization at known locations
- Long-term trends (erosion, sandbar shifts)

### What it CANNOT do (with foam % alone):
- Automated spot discovery (can't distinguish foam from snow/cloud/sand reliably)
- Break type classification at pixel level
- See individual waves (1-3 pixels per break)

### Multi-layer approach needed for spot finding:
1. **Differential foam maps** — subtract flat-day from swell-day, real breaks light up consistently
2. **Temporal stacking** — 20+ high-swell scenes, real breaks = same pixels repeatedly
3. **Swell-direction response** — real breaks only fire on specific directions
4. **Spatial pattern recognition** — point breaks = curved lines, beach = parallel bars
5. **Coastline geometry + bathymetry** — exposure, seafloor slope

### Current strategy: Visual Atlas first (manual browsing), then algorithm experiments with human labels as ground truth.

## Phase 4: Unified Ranking + Deployment — PLANNED
**Specs written:** See `.claude/SPEC-*.md` for detailed implementation plans.

- [x] **Unified spot ranking** — `20_rank_segments.py` computes composite 0-100 score (geometry 35pts + foam 40pts + profile 25pts). 374 segments with foam, 42 with full profiles. Known spots rank 88-100th percentile. Map updated with composite color coding + confidence badges.
- [ ] **Deployment** — Vercel for static hosting, Cloudflare R2 for image CDN, GitHub Actions CI/CD. Spec: `SPEC-deployment.md`

## Phase 5: Algorithm Experiments — PLANNED
- [ ] **Differential foam maps** — subtract flat-day from swell-day imagery
- [ ] **Temporal stacking** — aggregate 20+ high-swell scenes, persistent foam = real breaks
- [ ] **Swell-direction response** — compare foam maps across direction bins
- [ ] **Spatial pattern recognition** — point breaks = curved lines, beach = parallel bars
- [ ] **Ensemble scoring** — combine all signals with human labels as ground truth
- [ ] Full spec: `SPEC-algorithm-experiments.md`

## Phase 6: Data Quality Improvements — PLANNED
- [ ] **Cliff foam filter** — DEM-based coastline classification (beach/cliff/headland). Spec: `SPEC-cliff-foam-filter.md`
- [ ] **Bathymetry integration** — GEBCO nearshore slope for geometry scoring (fills skipped 20pt component). Spec: `SPEC-bathymetry-integration.md`

## Blockers
1. ~~Waiting on Graham's spot pins~~ — ✅ DONE (6 South Shore spots pinned Mar 25)
2. No cloud Supabase yet — local dev only until free tier opens up
3. ~~4 remaining spots need foam detection runs~~ — All spots processed (31 with gallery data)
