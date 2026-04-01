# WaveScout

Surf discovery from satellite imagery. WaveScout uses Sentinel-2 satellite data, coastline geometry, and ocean conditions to find and rank candidate surf zones along Nova Scotia's coast.

**Live demo:** [wavescout.vercel.app](https://wavescout.vercel.app) (coming soon)

## What It Does

WaveScout analyzes 1,000+ km of Nova Scotia coastline to identify where waves are likely breaking — and why. The pipeline:

1. **Segments the coastline** into ~16,900 sections (~500m each) and scores them on geometry: swell exposure, coastal complexity, and road access
2. **Detects foam/whitewater** from Sentinel-2 NIR imagery across years of satellite passes — water absorbs NIR (appears black), foam reflects it (bright white)
3. **Builds swell-response profiles** per segment: at what swell height does it turn on? What direction? When does it blow out?
4. **Ranks everything** with a composite score combining geometry (35%), foam evidence (40%), and swell profile quality (25%)

The result: 374 segments with foam data, 42 with full swell profiles, and known surf spots consistently ranking in the 88-100th percentile.

## Web Viewer

A Next.js app for exploring results interactively:

- **Map** — dark Mapbox map with three tiers: verified spots (teal), high-scoring candidates (orange), and all scored segments (gray on zoom)
- **Spot detail** — satellite gallery (RGB + NIR), swell-response charts, foam stats, tide/direction metadata
- **Atlas** — browse the entire surfable coastline in ~3km sections with satellite imagery across swell conditions
- **Compare** — cross-spot same-date comparison to see how different spots respond to the same swell

Pages: `/` (map), `/atlas`, `/compare`, `/methodology`, `/about`

## Key Technical Findings

- **NIR (B8) is the best band for foam detection** — far better contrast than true-color RGB
- **Moderate swell (1.6-2.0m) shows the clearest break patterns** — storm days are too blown out
- **Different spots have different swell thresholds** — there's no single "waves are breaking" cutoff
- **10m resolution can detect foam presence and extent** but not individual wave shapes
- **Open-Meteo swell data starts Oct 2021** for Nova Scotia; earlier scenes lack swell context

## Project Structure

```
pipeline/
  scripts/          20 numbered pipeline scripts (01-20) + build scripts
  configs/          spot + atlas section configs (JSON)
  data/             manifests, coastline data, gallery images, foam detections
docs/
  SPEC.md           full product spec
  METHODOLOGY.md    detection methodology explainer
  PRODUCT-VISION.md broader product direction
web/                Next.js 15 app (Mapbox GL, Recharts, Tailwind)
  src/app/          App Router pages
  src/components/   React components
  public/data/      optimized static data (built from pipeline)
```

## Setup

### Pipeline

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
earthengine authenticate
```

Requires a Google Earth Engine account and project. Set `GEE_PROJECT` in `.env`.

### Web Viewer

```bash
cd web
pnpm install
cp .env.local.example .env.local   # add your Mapbox token
pnpm dev                           # localhost:3000
```

### Rebuilding Web Data from Pipeline

```bash
python3 pipeline/scripts/build_web_data.py        # spots, segments, gallery
python3 pipeline/scripts/build_atlas_web_data.py   # atlas sections
```

## Tech Stack

- **Pipeline:** Python 3.12, Google Earth Engine (`earthengine-api`), Open-Meteo Marine + Weather APIs, PIL/numpy
- **Web:** Next.js 15, TypeScript, Tailwind CSS, Mapbox GL JS, Recharts
- **Data:** Sentinel-2 L2A imagery (10m resolution), OSM coastline geometry, Open-Meteo hindcast swell/wind

## Pipeline Scripts

| # | Script | What It Does |
|---|--------|-------------|
| 01 | `test_gee_access.py` | Scene inventory for a spot |
| 02 | `export_sample_images.py` | Export GeoTIFFs to Google Drive |
| 03 | `check_conditions.py` | Open-Meteo marine + weather lookup |
| 04 | `run_feasibility.py` | Orchestrate 01+03 across spots |
| 05 | `generate_review_sheet.py` | CSV review sheets for manual labeling |
| 06 | `generate_thumbnails.py` | True-color PNGs from GEE |
| 07 | `generate_band_composites.py` | NIR, SWIR, NDWI composites |
| 10 | `segment_coastline.py` | OSM coastline to 500m scored segments |
| 11 | `score_geometry.py` | Geometry scoring 0-100 |
| 12 | `calibrate.py` | Validate against 14 known spots |
| 13 | `detect_foam_nir.py` | NIR foam detection per segment per scene |
| 14 | `build_swell_profiles.py` | Swell-response profiles from foam data |
| 15-16 | `generate_gallery_*.py` | Satellite gallery thumbnails (RGB + NIR) |
| 17-18 | `tile_coastline.py` / `generate_atlas_fast.py` | Coastline atlas sections + images |
| 19 | `annotate_gallery.py` | Break pin annotations on gallery images |
| 20 | `rank_segments.py` | Unified composite scoring |

## Status

Active development. Current focus areas:
- Deployment to Vercel
- Algorithm experiments (differential foam maps, temporal stacking, spatial pattern recognition)
- Data quality improvements (cliff/foam filtering, bathymetry integration)

See [docs/SPEC.md](docs/SPEC.md) for the full product spec and [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for how the detection pipeline works.

## License

All rights reserved.
