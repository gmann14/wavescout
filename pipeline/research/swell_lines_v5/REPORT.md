# Swell-Line Detection V5 Report

*Status: review bank prepared; awaiting manual review labels. Owner: Graham Mann. Updated: 2026-04-24.*

## Scope

- Separate research track only. No production ranking changes.
- Same frozen 8-scene benchmark remains held out.
- New work in this branch is data-first:
  - freeze an expanded organized-scene development review set
  - collect manual labels
  - route to detector problem vs selection problem vs sensor/use-case problem

## Current State

- `scene_catalog.json` now uses the larger per-spot foam manifests instead of the curated gallery subset.
- the catalog was refreshed against GEE through `2026-04-24`
- `candidate_scenes.json` now freezes a broad-profile development review bank
- `scene_reviews.csv` is the manual review sheet.
- `summary.json` is computed from the current labels.
- current scene catalog size: `445` scene-level records across the 4 spots
- current refreshed scene count from GEE after the March manifests: `16`
- current frozen review set size: `33` organized candidates
- current shortfall vs the broad-profile `36`-scene target: `3`

Per spot:

- Cow Bay: `8` scenes total (`1` frozen + `7` additional)
- Lawrencetown Beach: `7` scenes total (`1` frozen + `6` additional)
- Hirtle's Beach: `9` scenes total (`1` frozen + `8` additional)
- Martinique Beach: `9` scenes total (`1` frozen + `8` additional)

At the moment this branch is not complete because the review labels have not been filled in yet.

The review CSV is now prefilled with local RGB/NIR review images for all `33` selected scenes under `pipeline/research/swell_lines_v5/review_images/`, so manual review can start immediately.

## Broad Review Profile

The current review bank was built with the broad profile:

- `cloud_pct <= 15`
- `quality_score >= 75`
- `swell_height_m >= 1.0`
- `swell_period_s >= 7.0`
- up to `8` additional organized candidates per spot

Reason: the stricter gallery-style profile was too narrow for a useful signal-validation pass. The held-out 8-scene benchmark remains unchanged.

## GEE Refresh

The local foam manifests ended at `2026-03-18`. A lightweight GEE refresh added new clear-scene metadata for:

- `2026-03-28`
- `2026-04-07`
- `2026-04-09`
- `2026-04-12`

Those dates were checked for all 4 spots and merged into `scene_catalog.json`.

## Review Workflow

Primary instructions:

- `pipeline/research/swell_lines_v5/REVIEW_INSTRUCTIONS.md`

Quick version:

1. Fill `scene_reviews.csv` using `clear_positive`, `ambiguous`, or `clear_negative`.
2. Add one short note per scene.
3. Run:

```bash
venv/bin/python pipeline/research/swell_lines_v5/summarize_reviews.py
```

The resulting `summary.json` is the official decision artifact for this spike.

## To-Do

- complete manual labels in `pipeline/research/swell_lines_v5/scene_reviews.csv`
- rerun `venv/bin/python pipeline/research/swell_lines_v5/summarize_reviews.py`
- write the final interpretation in this report after labels are complete
