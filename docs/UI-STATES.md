# WaveScout UI States

*Updated: 2026-04-17*  
*Status: Normative state matrix for release-grade viewer behavior*

## Purpose

This document removes ambiguity from page behavior. Each user-facing surface must implement the states below before MVP release.

## Global Rules

- every blocking state must have visible copy
- every recoverable error must have a retry or escape route
- low-confidence and degraded-quality states must be explicit
- loading spinners alone are not sufficient

## Global Navigation

### `nav-ready`

Visible:

- all five routes
- active-route styling
- Nova Scotia region label

### `nav-overflow-mobile`

Visible:

- the same five routes in a mobile-usable layout

Release rule:

- no route may become unreachable on small screens

## Map Page

### `map-loading`

Trigger:

- initial data fetch before map-ready state

Must show:

- map shell placeholder
- `Loading WaveScout dataset...`

### `map-config-error`

Trigger:

- missing `NEXT_PUBLIC_MAPBOX_TOKEN`

Must show:

- operator-facing error
- `Map token missing. Set NEXT_PUBLIC_MAPBOX_TOKEN to render the map.`

### `map-data-error`

Trigger:

- any required map dataset fails to load

Must show:

- `Map data failed to load.`
- retry action or refresh instruction

### `map-empty`

Trigger:

- datasets load but contain zero displayable items

Must show:

- `No map data is available for this dataset.`

### `map-ready-no-selection`

Trigger:

- datasets loaded and no feature selected

Must show:

- legend
- explanation of confirmed vs candidate vs context-only layers

### `map-ready-selection-confirmed`

Trigger:

- user selects a named public confirmed spot

Must show:

- detail panel in confirmed mode
- named location header
- score and confidence

### `map-ready-selection-candidate`

Trigger:

- user selects a candidate segment or section

Must show:

- detail panel in candidate mode
- candidate label
- uncertainty and caution language

### `map-ready-selection-low-confidence`

Trigger:

- selected entity has `evidence_confidence_level <= 1`

Must show:

- caution banner
- `Evidence is limited. Treat this as an exploratory lead, not a dependable result.`

## Detail Panel

### `panel-closed`

Trigger:

- no feature selected

Requirement:

- no hidden focus trap

### `panel-loading`

Trigger:

- feature selected and detail payload still loading

Must show:

- header with entity name if available
- `Loading details...`

### `panel-ready-full`

Trigger:

- detail payload loaded with explanation, gallery, and profile

Must show:

- entity label
- verification/publication status
- surf potential score
- evidence confidence
- explanation summary
- highlights
- caveats
- gallery
- profile summary
- provenance

### `panel-ready-no-gallery`

Trigger:

- detail payload loaded without gallery-eligible scenes

Must show:

- all non-gallery content
- `No gallery scenes are available for this location yet.`

### `panel-ready-no-profile`

Trigger:

- detail payload loaded but profile is ineligible

Must show:

- all non-profile content
- `Profile not available yet. More clean observations are required before showing a swell-response summary.`

### `panel-ready-degraded`

Trigger:

- `quality_status == "degraded"`

Must show:

- degraded evidence banner
- `Some supporting scenes are degraded by contamination or limited coverage.`

### `panel-error`

Trigger:

- detail payload fails to load

Must show:

- `Details failed to load.`
- close action

## Atlas Page

### `atlas-loading`

Must show:

- atlas shell placeholder
- `Loading coastline atlas...`

### `atlas-empty`

Trigger:

- `sections.json` loads with zero features

Must show:

- `No atlas sections are available for this dataset.`

### `atlas-ready-no-selection`

Must show:

- atlas legend
- explanation that atlas sections are browsing units, not confirmed breaks

### `atlas-ready-selection-with-scenes`

Must show:

- section summary
- mean and max score
- scene gallery

### `atlas-ready-selection-no-scenes`

Trigger:

- section exists but gallery scenes missing

Must show:

- section summary
- `No atlas imagery is available for this section yet.`

## Compare Page

### `compare-loading`

Must show:

- `Loading comparison data...`

### `compare-error`

Must show:

- `Comparison data failed to load.`

### `compare-empty`

Trigger:

- no compare-eligible dates

Must show:

- `No same-date comparisons are available for this dataset.`

### `compare-ready-default`

Trigger:

- default view with date groups meeting the `3`-spot threshold

Must show:

- filter controls
- explanation that all cards share the same acquisition date within a row

### `compare-ready-sparse-date`

Trigger:

- `date` query param forces a date with fewer than `3` spots

Must show:

- sparse comparison banner
- `This date has limited coverage and is shown because it was requested directly.`

### `compare-no-match`

Trigger:

- `date` query param does not match any compare-eligible scenes

Must show:

- `No comparison scenes were found for this date.`
- link back to `/compare`

## How It Works Page

### `methodology-ready`

Must show:

- plain-language explanation
- limitations
- caution around precision

### `methodology-missing`

Trigger:

- markdown file missing or unreadable

Must show:

- `Methodology content is unavailable in this build.`

## About Page

### `about-ready`

Must show:

- mission
- scope boundary
- safety/access/uncertainty caveat

## Accessibility Checks

Every state above must satisfy:

- keyboard reachable controls
- visible focus
- no color-only differentiation for important status
- screen-reader-friendly labels on panel close, gallery toggles, and map-adjacent controls
