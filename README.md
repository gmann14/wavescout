# WaveScout

WaveScout is a feasibility-first prototype for surf discovery using satellite imagery, coastline geometry, and ocean conditions data.

The project starts with Nova Scotia. The current repository is focused on answering one question:

**Can Sentinel-2 imagery provide useful surf evidence at known spots?**

The broader product plan lives in [docs/SPEC.md](docs/SPEC.md).

## Current Scope

This repo currently supports Phase 1 feasibility work:

- load a checked-in region config for any known spot
- verify Google Earth Engine access
- inspect Sentinel-2 scene availability for a configured spot
- export sample scenes for manual review
- query historical marine and weather conditions for selected dates
- run the full feasibility pipeline across multiple spots
- generate observation review sheets for manual imagery labeling
- write JSON manifests with processing-run provenance for each step

It is **not yet** a general coastline-processing pipeline or a polished any-coastline CLI.

## Setup

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
earthengine authenticate
```

Notes:

- `earthengine authenticate` requires browser-based OAuth
- `coastsat` is not installed by `requirements.txt`; it remains optional for later phases
- the scripts currently assume a working Earth Engine account and default project setup
- the default region config is `pipeline/configs/lawrencetown.json`

## Prototype Workflow

### Quick start: single spot

Run from the project root:

```bash
python3 pipeline/scripts/01_test_gee_access.py
python3 pipeline/scripts/02_export_sample_images.py
python3 pipeline/scripts/03_check_conditions.py --dates-file pipeline/data/manifests/lawrencetown-beach_scene_inventory.json
```

### Multi-spot feasibility run

Run the full pipeline across all configured spots:

```bash
python3 pipeline/scripts/04_run_feasibility.py
```

Or select specific spots:

```bash
python3 pipeline/scripts/04_run_feasibility.py --spots lawrencetown-beach cow-bay martinique-beach
```

After exporting and reviewing imagery, generate review sheets:

```bash
python3 pipeline/scripts/05_generate_review_sheet.py --all
```

## Scripts

- `01_test_gee_access.py`
  - reads region metadata from a JSON config
  - checks Earth Engine initialization
  - counts Sentinel-2 scenes over the configured test area
  - prints sample dates and available bands
  - writes a scene inventory manifest to `pipeline/data/manifests/`

- `02_export_sample_images.py`
  - reads region metadata from a JSON config
  - exports up to 20 configured Sentinel-2 scenes to Google Drive
  - intended for manual review of visible white water or breaking-wave signal
  - writes an export manifest to `pipeline/data/manifests/`

- `03_check_conditions.py`
  - reads point location from the region config unless overridden
  - queries Open-Meteo Marine API for wave/swell data and Open-Meteo Weather API for wind data
  - uses the archive endpoint for historical dates, forecast endpoint for recent dates
  - accepts dates as CLI arguments or extracts them from a saved manifest
  - writes a conditions manifest with separate `marine` and `weather` sections per observation

- `04_run_feasibility.py`
  - orchestrates scripts 01 and 03 across all spot configs (or a selected subset)
  - optionally includes image export (02) with `--export`
  - produces a combined feasibility manifest with processing-run ID, code version, and data source provenance

- `05_generate_review_sheet.py`
  - reads scene inventory and conditions manifests for a spot
  - generates a CSV with pre-filled conditions data
  - reviewer fills in `observation_label` (present / none / unclear) and notes
  - output goes to `pipeline/data/reviews/`

- `_script_utils.py`
  - shared utilities: config loading, manifest paths, JSON writing
  - `generate_run_id()` and `build_run_manifest()` for processing-run provenance
  - `get_code_version()` captures the current git commit hash

## Data

### Checked In

- `pipeline/configs/lawrencetown.json` — Lawrencetown Beach (default)
- `pipeline/configs/cow-bay.json` — Cow Bay reef break
- `pipeline/configs/martinique-beach.json` — Martinique Beach

- `pipeline/data/ns_known_spots.geojson`
  - 14 known Nova Scotia surf spots used for calibration and sanity checks

- `pipeline/data/known_spots/naotokui_surfspots.json`
- `pipeline/data/known_spots/msw_surfspots.csv`
- `pipeline/data/known_spots/osm_surfspots.json`
- `pipeline/data/known_spots/wannasurf_portugal.kmz`

The global spot datasets are reference material for later calibration or ML experiments. They are not yet part of the current prototype workflow.

### Generated (gitignored)

- `pipeline/data/manifests/` — JSON manifests from each script run
- `pipeline/data/reviews/` — CSV review sheets for manual imagery labeling

### External Dependencies

- Sentinel-2 imagery via Google Earth Engine
- marine conditions via Open-Meteo Marine API
- wind conditions via Open-Meteo Weather API (archive endpoint for historical, forecast for recent)
- bathymetry via GEBCO when the project moves beyond feasibility work

## Status

Status: Phase 1 feasibility prototype.

Current decision gate:

1. Can known Nova Scotia spots show recognizable surf signal in clear Sentinel-2 scenes?
2. Do observed scene dates line up directionally with plausible marine and wind conditions?
3. Is the signal strong enough to justify imagery-assisted ranking, or should the project pivot to geometry-first ranking?

## Near-Term Next Steps

1. Run `earthengine authenticate` to set up GEE access.
2. Run `04_run_feasibility.py` to inventory scenes and check conditions across all spots.
3. Export review sets with `02_export_sample_images.py` for each spot.
4. Generate review sheets with `05_generate_review_sheet.py --all`.
5. Manually inspect scenes and fill in observation labels.
6. Write down a go / no-go decision for imagery-assisted feasibility.

## Output Expectations

At this stage, useful outputs are simple:

- scene inventories per spot
- exported imagery for review
- conditions tables with marine and weather data
- per-step JSON manifests with region metadata, query settings, and run provenance
- CSV review sheets with observation labels and notes
- a written feasibility decision

The static web viewer and reproducible Nova Scotia dataset described in the spec come later.
