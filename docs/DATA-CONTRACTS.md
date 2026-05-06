# WaveScout Data Contracts

*Updated: 2026-05-05*  
*Status: Normative contract for payload shape, field semantics, and public dataset packaging*

## Purpose

This document defines the target contract for the static dataset consumed by the web app and used for release validation.

If this document conflicts with an implementation detail, this document wins.

## Precedence

The contract stack is:

1. [SPEC.md](SPEC.md) for product scope and release rules
2. [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md) for disclosure rules
3. this document for payload and field shape
4. implementation files and generated artifacts

## Key Decision

The current repo contains working payloads, but they are not yet the target public contract. In particular:

- `confidence` is overloaded today and must be split
- explanation data is available in some pipeline artifacts but not propagated everywhere
- publication status is not modeled explicitly
- `web/public/data/spots/manifest.json` exists but is not part of the canonical web contract

## Required Promoted Dataset Layout

The promoted dataset must expose exactly these supported files:

```text
web/public/data/
  dataset-manifest.json
  spots.json
  segments-high.json
  segments-all.json
  gallery.json
  methodology.md
  spots/
    <slug>.json
  atlas/
    sections.json
    gallery.json
```

The following are explicitly unsupported as public contract inputs:

- `web/public/data/spots/manifest.json`
- any pipeline manifest copied directly into the web app without normalization

## Common Field Semantics

### Identifier Fields

- `slug`: stable lowercase identifier for a spot-like entity
- `id`: stable identifier for a segment or section
- `run_id`: immutable processing-run identifier

### Score Fields

- `surf_potential_score`: number in `[0, 100]`
- `evidence_confidence_level`: integer in `[0, 3]`
- `evidence_confidence_label`: one of `none`, `low`, `moderate`, `high`

Mapping:

| Level | Label | Meaning |
|---|---|---|
| 0 | `none` | no usable evidence beyond baseline metadata |
| 1 | `low` | geometry-only or highly sparse evidence |
| 2 | `moderate` | usable imagery evidence or partial profile support |
| 3 | `high` | repeated usable evidence with completed profile support |

### Verification And Publication Fields

These must be modeled separately.

- `verification_status`: one of `confirmed`, `candidate`, `rejected`
- `publication_status`: one of `public_named`, `public_coarse`, `internal_only`

Rules:

- `verification_status` answers whether the location is believed to be a real surf-relevant place
- `publication_status` answers how precisely it may be shown
- no payload may infer `publication_status` from `verification_status`

### Quality Fields

- `quality_status`: one of `usable`, `degraded`, `rejected`
- `quality_score`: numeric quality score in `[0, 100]`

Rules:

- `usable` means safe to show without warning banner
- `degraded` means show with caution text
- `rejected` means do not use for default gallery/profile calculations

Score-to-status mapping:

- `usable`: `quality_score >= 90`
- `degraded`: `60 <= quality_score < 90`
- `rejected`: `quality_score < 60`

### Enumerated Type Fields

- `break_type`: one of `beach`, `point`, `reef`, `slab`, `mixed`, `unknown`

### Provenance Fields

Each public payload must be traceable to dataset provenance.

Required provenance fields:

- `run_id`
- `generated_at_utc`
- `code_version`
- `config_version`

If a value cannot be resolved at build time, it must be written as `"unknown"`, not omitted.

## Explanation Object

Every selectable public entity must expose an `explanation` object.

Required shape:

```json
{
  "summary": "Short plain-English explanation.",
  "score_components": {
    "geometry": 28.0,
    "foam": 34.9,
    "profile": 0.0
  },
  "highlights": [
    "Faces primary swell window",
    "Repeated usable imagery evidence"
  ],
  "caveats": [
    "Profile incomplete",
    "Bathymetry is coarse"
  ],
  "provenance": {
    "run_id": "20bedc0157f3",
    "generated_at_utc": "2026-03-30T16:17:32.613090+00:00",
    "code_version": "02614df",
    "config_version": "unknown"
  }
}
```

Rules:

- `summary` is required and must be plain language
- `highlights` and `caveats` must each contain at least one item
- `score_components` must use numeric values, not prose strings
- provenance must be embedded or linked by stable identifier

## Payload Contracts

### `dataset-manifest.json`

Purpose:

- single source of truth for the promoted dataset

Required fields:

- `dataset_id`
- `region`
- `status`
- `run_id`
- `generated_at_utc`
- `code_version`
- `config_version`
- `source_manifests`
- `artifacts`

`status` must be one of:

- `draft`
- `promoted`
- `retired`

### `spots.json`

Type:

- GeoJSON `FeatureCollection<Point>`

Supported audience:

- named, publicly displayable reference entries only

Required `properties`:

- `name`
- `slug`
- `break_type`
- `verification_status`
- `publication_status`
- `source_summary`
- `short_summary`
- `surf_potential_score`
- `evidence_confidence_level`
- `evidence_confidence_label`
- `gallery_available`
- `swell_profile_available`
- `quality_status`
- `foam_summary`
- `explanation`

Optional:

- `swell_window_summary`

Forbidden:

- legacy `confidence` string

### `segments-high.json`

Type:

- GeoJSON `FeatureCollection<Point>`

Purpose:

- selectable candidate segment layer

Required `properties`:

- `id`
- `verification_status`
- `publication_status`
- `map_display_eligible`
- `surf_potential_score`
- `evidence_confidence_level`
- `evidence_confidence_label`
- `quality_status`
- `coastal_exposure_class`
- `coastal_context_penalty`
- `nearfield_open_water_deg`
- `nearfield_blocked_ratio`
- `farfield_open_water_deg`
- `farfield_blocked_ratio`
- `score_components`
- `foam_obs_count`
- `turn_on_threshold_m`
- `optimal_swell_range`
- `primary_direction`
- `explanation`

Optional:

- `orientation_deg`
- `exposure_arc_deg`
- `rank`

Rules:

- `map_display_eligible` determines whether the segment may appear on the main `Map` page as a public lead-browsing candidate
- `Atlas` may remain broader than `Map`
- `map_display_eligible` must be generated data, not an undocumented UI-only heuristic
- `coastal_exposure_class` must be one of `open_coast`, `outer_coast`, `semi_sheltered`, or `sheltered_inner_coast`
- `coastal_context_penalty` must be a deterministic numeric penalty derived from generated coastal context, not hand-edited UI logic
- `nearfield_open_water_deg` must represent immediate open-water degrees in the primary seaward fan
- `nearfield_blocked_ratio` must represent the fraction of nearfield fan rays blocked by opposing coastline
- `farfield_open_water_deg` must represent broader open-water degrees farther seaward in the same primary fan
- `farfield_blocked_ratio` must represent the fraction of farther-field fan rays blocked by opposing coastline

### `segments-all.json`

Type:

- GeoJSON `FeatureCollection<Point>`

Purpose:

- non-interactive context layer only

Required `properties`:

- `id`
- `surf_potential_score`
- `evidence_confidence_level`

Explicit exemption:

- this file is exempt from the full explanation requirement because it is a context-only layer, not a selectable detail surface

If this layer becomes selectable later, it must graduate to the `segments-high.json` contract.

### `spots/<slug>.json`

Purpose:

- detail payload for a named public spot

Required fields:

- `slug`
- `name`
- `verification_status`
- `publication_status`
- `surf_potential_score`
- `evidence_confidence_level`
- `evidence_confidence_label`
- `quality_status`
- `explanation`
- `foam_summary`
- `swell_profile`
- `gallery_summary`
- `provenance`

`swell_profile` may be `null` only if the spot fails the profile eligibility threshold.

### `gallery.json`

Purpose:

- image-gallery manifest for compare and spot detail surfaces

Required top-level fields:

- `run_id`
- `generated_at_utc`
- `code_version`
- `parameters`
- `spots`
- `summary`

Each spot entry must contain:

- `spot_name`
- `slug`
- `publication_status`
- `scenes`

Each scene entry must contain:

- `date`
- `scene_id`
- `quality_status`
- `quality_score`
- `swell_height_m`
- `swell_period_s`
- `swell_direction_deg`
- `cloud_pct`
- `foam_fraction`
- `bin_label`
- `rgb_path`
- `nir_path`

Optional:

- `annotated_rgb_path`
- `annotated_nir_path`
- `tide_m`
- `tide_state`
- `wave_energy`

Rules:

- `scene_id` must uniquely identify the acquisition for that spot-date combination
- if `quality_status` is `rejected`, the scene must not appear in default compare results
- if a true upstream scene id is unavailable, build `scene_id` as `<slug>:<date>`
- every non-null image path must be web-root-relative, for example `/gallery/{slug}/{filename}.png`
- every non-null image path must resolve to a real file under `web/public/`
- `web/public/gallery/` is a deployable release artifact, not a local-only cache
- local and CI validation must fail if a manifest references an image missing from `web/public/`

Internal-only companion artifact:

- `pipeline/data/gallery/reference-bank-manifest.json` may exist as a denser non-public scene bank
- it is allowed to use relaxed scene-selection thresholds for manual research
- it must not be copied into `web/public/data/`
- it must not be treated as part of the promoted public dataset contract

### `atlas/sections.json`

Type:

- GeoJSON `FeatureCollection<Polygon>`

Required `properties`:

- `section_id`
- `publication_status`
- `mean_score`
- `max_score`
- `segment_count`
- `coastline_length_m`

Optional:

- `segment_ids`
- `centroid_lat`
- `centroid_lon`

### `atlas/gallery.json`

Required top-level fields:

- `run_id`
- `generated_at_utc`
- `code_version`
- `parameters`
- `sections`
- `summary`

Each section entry must contain:

- `section_id`
- `section_name`
- `slug`
- `publication_status`
- `mean_score`
- `max_score`
- `segment_count`
- `coastline_length_m`
- `scenes`

Rules:

- every non-null image path must be web-root-relative, for example `/atlas-gallery/{slug}/{filename}.png`
- every non-null image path must resolve to a real file under `web/public/`
- `web/public/atlas-gallery/` is a deployable release artifact when atlas gallery scenes are present

## Eligibility Thresholds

These phrases are now locked.

### Gallery Eligible

A scene is gallery-eligible only if all are true:

- `quality_score >= 90`
- `quality_status != "rejected"`
- at least one of `rgb_path` or `nir_path` exists

### Compare Eligible

A scene is compare-eligible only if all are true:

- gallery-eligible
- normalized `date` exists

A date is compare-eligible by default only if:

- at least `3` unique public spots have compare-eligible scenes on the same date

The `date` query parameter may lower this threshold to `1`, but the UI must mark the result as sparse comparison.

### Swell Profile Eligible

A location may display a swell-profile summary only if all are true:

- at least `30` clean observations
- at least `3` non-empty swell bins
- profile build status is complete

If any criterion fails:

- the detail payload must return `swell_profile: null`
- the UI must show `Profile not available yet` rather than partial numeric claims

## Derived Object Shapes

### `score_components`

Required fields:

- `geometry`
- `foam`
- `profile`

Values:

- numeric component contributions in score units, not prose strings

### `foam_summary`

Required fields:

- `scenes_processed`
- `segments_processed`
- `total_detections`
- `errors`
- `scenes_with_foam`
- `date_range`

Optional:

- `quality`

### `swell_profile`

Required fields when non-null:

- `swell_bins`
- `direction_bins`
- `turn_on_threshold_m`
- `optimal_range`
- `blow_out_point_m`
- `total_observations`
- `segment_count`

### `gallery_summary`

Required fields:

- `scene_count`
- `usable_scene_count`
- `degraded_scene_count`
- `latest_scene_date`

## Derived Boolean Rules

- `gallery_available = true` only if the entity has at least one gallery-eligible scene
- `swell_profile_available = true` only if the entity meets the swell-profile eligibility threshold

## Coordinate Precision Rules

Payload writers must honor [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md).

Minimum contract:

- `public_named`: full public geometry allowed
- `public_coarse`: coordinates rounded to `3` decimal places or section-level polygon only
- `internal_only`: must not appear in the public web dataset

## Backward Compatibility Rules

- legacy fields may remain during migration, but new code must read the normalized fields first
- once normalized fields are available everywhere, legacy `confidence` must be removed from public payloads
- unsupported files must not be read by the web app
