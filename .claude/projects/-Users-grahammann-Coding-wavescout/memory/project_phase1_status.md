# Phase 1 Feasibility Status

**Last updated:** 2026-03-24

## Completed
- GEE authenticated, project=seotakeoff via .env
- .env loaded via python-dotenv in _script_utils.py
- Feasibility pipeline ran for all 3 spots (lawrencetown-beach, cow-bay, martinique-beach)
- Scene inventories: ~306 clear scenes per spot (2017-2026)
- Conditions manifests: 20 dates per spot with marine + weather data
- Exported 24 GeoTIFF scenes to Google Drive (8 per spot, summer 2025, <15% cloud)
- Review CSVs generated (306-307 rows each) in pipeline/data/reviews/
- Web viewer built at web/index.html (static HTML, loads manifests)
- FEASIBILITY-STATUS.md written with findings and next steps

## Key Data Points
- ~1,100 total Sentinel-2 scenes per spot, ~28% clear rate
- Open-Meteo marine data available from ~2019 onward (null before)
- Weather (wind) data available for all dates via ERA5 archive
- All spots on same tile T20TMQ

## Awaiting
- Manual imagery review (download GeoTIFFs from Drive, inspect in QGIS)
- Fill in review sheet observation_label columns
- Go/no-go decision on imagery-assisted feasibility

## Architecture Notes
- Scripts use PYTHONPATH=pipeline/scripts to resolve _script_utils
- Export script sorts by date descending (most recent first)
- Conditions limited to 20 dates per spot via --conditions-limit in 04_run_feasibility.py
