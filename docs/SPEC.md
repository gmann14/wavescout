# WaveScout Product Spec

*Drafted: 2026-03-23*  
*Last updated: 2026-03-30*
*Status: Working spec — feasibility passed, pipeline + web viewer operational*

### Revision Notes

- 2026-03-30: Status update — all phases through 2.7 complete. Atlas browser built. Product direction shifted toward visual atlas for manual spot discovery, with algorithm experiments planned as Phase 5.
- 2026-03-23: Reframed around a feasibility gate, narrowed MVP to a static Nova Scotia explorer, and added provenance-first processing guidance.

---

## Overview

WaveScout is a surf discovery tool that analyzes coastline geometry, coarse bathymetry, and satellite imagery to identify candidate surf zones and explain why they may work.

The project starts with Nova Scotia. The first goal is not "find hidden spots everywhere." The first goal is to prove that the pipeline can recover signal at known spots and rank plausible candidate coastline segments above obvious non-spots.

This spec is intentionally stage-gated. The core technical risk is still unresolved: whether Sentinel-2 imagery provides a reliable enough surf signal to be useful for this product.

---

## Product Thesis

Discovering surf spots is slow, local, and inconsistent. Existing tools mostly help with forecasted conditions for already-known breaks. WaveScout aims to help with the earlier part of the problem:

- find coastline segments worth investigating
- explain what evidence supports that ranking
- correlate observed surf signal with historical conditions when possible

WaveScout is an exploration tool, not a guarantee that a spot is good, accessible, or safe.

---

## Users

Primary users:

- Nova Scotia surfers exploring beyond the best-known breaks
- traveling surfers researching unfamiliar coastlines
- technically curious surf explorers who want evidence, not just spot names

Secondary users:

- coastal researchers
- geospatial and ocean-data hobbyists

---

## Product Principles

1. Evidence before confidence. The app should show why a segment is ranked, not hide behind a black-box score.
2. Feasibility before platform. Do not build a large web product before validating the imagery signal.
3. Heuristics before ML. Start with transparent scoring and calibration. Add learned models only after the label quality is good enough.
4. Static results first. MVP serves precomputed regions only.
5. Provenance matters. Every score must be traceable to a processing run, data inputs, and config version.

---

## Feasibility Gate

Before committing to a full product MVP, the project must answer one question:

**Can Sentinel-2 imagery contribute useful surf evidence at known Nova Scotia spots?**

### Feasibility Success Criteria

WaveScout passes the feasibility gate if all of the following are true:

1. At least 3 known Nova Scotia spots show manually recognizable breaking-wave or white-water signal in a meaningful subset of clear Sentinel-2 scenes.
2. Retrieved marine conditions for those scenes are directionally consistent with what those spots are expected to work on.
3. The same review method can distinguish at least some known spots from obvious non-surf coastline.
4. The result can be reproduced from scripts and checked-in config, not only manual ad hoc exploration.

The feasibility bar is intentionally lower than "recover all known spots." The current 14-spot seed set is for calibration, but some spots may be too sheltered, too small, or too ambiguous to show useful signal at 10 m resolution. Early success means recovering a meaningful subset, not perfect recall.

If the feasibility gate fails, the project does **not** stop. It pivots to a geometry-first product:

- rank coastline segments using exposure, coastal shape, bathymetry, and access
- use imagery as supporting context only
- defer image-based surf detection and conditions correlation to a later phase

---

## Current Prototype Scope

The repository currently supports an early Phase 1 prototype:

- load a checked-in region config
- test Google Earth Engine access
- inspect Sentinel-2 scene availability for a configured spot
- export sample images for manual review
- query historical marine conditions for selected image dates
- write JSON manifests for each prototype step

Checked-in calibration data currently includes **14** Nova Scotia known spots in `pipeline/data/ns_known_spots.geojson`.

Expected usage of that seed set:

- a smaller subset should be used for feasibility review, prioritizing exposed and visually legible spots
- the full 14 can still be used later for calibration and sanity checks

This is enough to validate feasibility. It is not yet a general coastline-processing pipeline.

---

## MVP Definition

MVP means a usable, static Nova Scotia explorer built on precomputed data.

### MVP Includes

1. **Preprocessed Nova Scotia dataset**
   - coastline segmented into candidate sections
   - confirmed known spots included as reference entries
   - candidate sections ranked by a transparent heuristic score

2. **Static web map**
   - Nova Scotia only
   - confirmed vs candidate markers or segments
   - filter by score band and evidence availability

3. **Spot or segment detail panel**
   - score and explanation
   - sample satellite observations when available
   - basic conditions summary when enough observations exist
   - coarse bathymetry and exposure summary
   - nearest road distance or access estimate, if available

4. **Reproducible processing pipeline**
   - config-driven run for Nova Scotia
   - outputs GeoJSON plus run metadata
   - reruns produce a new processing record, not silent overwrites

### MVP Does Not Include

- live "working today" forecasts
- user-triggered processing from the web UI
- mobile app
- exact tide prediction
- automatic naming of secret or user-contributed spots
- global any-coastline support as a polished workflow
- ML-based spot classification as a requirement

---

## Non-Goals for This Spec

The following may happen later, but they are not gating MVP:

- training a multi-input CNN
- high-resolution commercial imagery
- crowd verification and moderation systems
- forecasting based on future swell conditions
- support for every coastline through a polished self-serve CLI

---

## Success Metrics

### Feasibility Metrics

- known-spot recovery rate on the seed set
- number of manually validated surf-signal scenes at known spots
- precision of candidate ranking versus obvious non-surf coastline in sampled reviews

### MVP Metrics

- at least one Nova Scotia dataset processed end to end with reproducible outputs
- map loads and renders static results without server-side recomputation
- every displayed candidate has an explanation payload
- known reference spots are not systematically ranked below poor candidates

---

## User Experience

### Web Viewer (MVP)

The web viewer serves precomputed results only.

- region selector can start with a single option: `Nova Scotia`
- user browses map and detail views
- no background job creation
- no map-drawing interface

### Developer Workflow

The developer workflow is config-driven, not fully self-serve yet.

- start with a checked-in region config for Nova Scotia
- later add a bounding-box based CLI for other coastlines
- document assumptions and dataset prerequisites clearly

---

## Ethics and Release Policy

This is a product requirement, not a side note.

Default MVP policy:

- confirmed public spots can be shown directly
- candidate discoveries should be displayed as coastline segments, not hyper-precise "secret reef" pins
- public outputs should round or coarsen exact coordinates where appropriate
- the site should include a takedown or report mechanism
- the UI should emphasize access, safety, and uncertainty

This policy can be tightened later if the output proves too sensitive.

---

## Data Sources and Constraints

### Sentinel-2 via Google Earth Engine

Primary use:

- visual evidence of white water, breaking patterns, and coastal context

Important constraints:

- 10 m resolution may be too coarse for many breaks
- revisit cadence plus cloud cover severely limits usable observations
- scene-level cloud percentage is not enough; per-pixel masking is required

### Open-Meteo Marine API

Primary use:

- hourly marine conditions near observation time
- wave height, wave direction, wave period
- swell components and coarse sea-level context fields

Important constraint:

- nearshore accuracy is limited
- if used, the relevant field is Open-Meteo Marine's hourly sea-level value and should be treated only as coarse sea-level context
- the returned sea-level field is **not** a substitute for a local tide table
- this data is suitable for coarse correlation, not exact break prediction

### Open-Meteo Weather API

Chosen weather source for MVP wind fields.

Use it for:

- hourly wind speed near capture time
- hourly wind direction near capture time

This keeps marine and weather joins explicit and avoids overloading the marine endpoint.

### GEBCO Bathymetry

Primary use:

- shelf gradient
- large offshore features
- coarse exposure context

Important constraint:

- too coarse for resolving individual sandbars, channels, or small reefs

### Known Spot Seed Data

Current checked-in calibration set:

- `pipeline/data/ns_known_spots.geojson`
- **14** confirmed Nova Scotia spots

This seed set is for calibration and evaluation. It is too small and too noisy to justify a production ML classifier by itself.

### Roads / Coastline Geometry

Likely sources:

- OSM or Overture-derived coastline and road data

Used for:

- coastline segmentation
- access heuristics
- harbor and developed-waterfront filtering

---

## Product Architecture

```text
Data Sources
  Sentinel-2 imagery
  Marine conditions
  Weather conditions
  GEBCO bathymetry
  Coastline + roads
  Known spots seed set

        |
        v

Processing Run
  region config
  date bounds
  feature config
  scoring weights
  code version

        |
        v

Derived Artifacts
  coastline segments
  candidate sections
  satellite observations
  spot or segment scores
  static output bundle

        |
        v

Delivery
  static GeoJSON
  optional database load
  static web viewer
```

---

## Analysis Approach

### Stage 1: Coastline Segmentation

For the target region:

- extract exposed coastline
- segment into fixed-length coastal sections
- exclude obvious non-target areas where possible:
  - harbors
  - docks
  - inland water
  - heavily urban waterfront

Initial segment length should be treated as a tunable parameter. `500m` is a starting point, not a hard requirement.

To reduce boundary effects, segmentation should use overlap or sliding windows. A reasonable starting point is `500m` segments with `250m` stride, then merge or suppress near-duplicate candidates downstream.

### Stage 2: Transparent Geometry Heuristics

Compute features such as:

- coastal orientation
- exposure to dominant swell windows
- bay or headland geometry
- nearby river mouths
- offshore island or reef context
- coarse bathymetric slope
- proximity to roads or trails

This stage should produce a cheap filter and a human-readable explanation.

### Stage 3: Imagery Evidence

For the most plausible candidate segments and known calibration spots:

- retrieve clear Sentinel-2 scenes
- mask clouds and invalid pixels
- inspect white-water or surf-signal evidence
- label scenes as:
  - surf signal present
  - no surf signal
  - unclear

MVP should assume this starts as manual or semi-automated review. A fully automated classifier is optional.

### Stage 4: Conditions Correlation

For observations labeled `surf signal present`:

- store precise image timestamp
- join hourly marine conditions near capture time
- join wind conditions from a weather source if needed
- optionally store the Open-Meteo hourly sea-level value as coarse tidal context, not exact tide

The product language should say "observed conditions near capture time," not "this spot works on tide X" unless the data quality justifies that claim.

### Stage 5: Scoring

MVP scoring should remain interpretable.

Recommended score components:

- geometry and exposure score
- bathymetry context score
- imagery evidence count
- imagery evidence quality
- calibration adjustment against known spots
- optional access modifier

Avoid a single unexplained "AI confidence" number.

---

## Scoring Semantics

Two concepts should stay separate:

### Surf Potential Score

How promising the segment looks as a surf location based on all available evidence.

### Evidence Confidence

How strong the supporting data is for that score.

Examples:

- high potential, low evidence: geometry looks excellent but imagery is sparse
- moderate potential, high evidence: repeated imagery signal but limited bathymetric support

This is clearer than a single blended confidence value.

---

## Data Model

The schema should support provenance and reruns.

### `processing_runs`

One row per pipeline execution.

Suggested fields:

- `id`
- `region`
- `bbox`
- `start_date`
- `end_date`
- `config_version`
- `code_version`
- `created_at`
- `notes`

### `spots`

Represents confirmed spots or derived candidate segments.

Suggested fields:

- `id`
- `processing_run_id`
- `name`
- `kind` (`confirmed` or `candidate`)
- `lat`
- `lng`
- `segment_geometry`
- `region`
- `surf_potential_score`
- `evidence_confidence`
- `geometry_score`
- `bathymetry_score`
- `imagery_evidence_count`
- `access_score`
- `break_type_predicted`
- `explanation_json`
- `created_at`

### `satellite_observations`

One row per scene-segment observation.

Suggested fields:

- `id`
- `processing_run_id`
- `spot_id`
- `sentinel_product_id`
- `image_timestamp`
- `observation_label` (`present`, `none`, `unclear`)
- `observation_confidence`
- `cloud_cover_scene`
- `marine_conditions_json`
- `weather_conditions_json`
- `thumbnail_url`
- `created_at`

This is intentionally more flexible than locking many fields into top-level columns too early.

### `explanation_json`

This field is a core product surface because users need to understand why something is ranked.

Suggested shape:

```json
{
  "summary": "South-facing coastal segment with strong swell exposure and repeated surf-signal observations in clear scenes.",
  "score_components": {
    "geometry": 0.82,
    "bathymetry": 0.55,
    "imagery_evidence": 0.67,
    "access": 0.40
  },
  "highlights": [
    "Faces primary S-SE swell window",
    "Headland geometry may focus energy",
    "3 of 9 reviewed clear scenes showed surf signal"
  ],
  "caveats": [
    "Bathymetry is coarse",
    "Wind correlation based on sparse observations"
  ]
}
```

---

## Output Contract

The pipeline should emit a portable output bundle for the web viewer.

Minimum output:

- `spots.geojson`
- optional observation summary JSON for detail panels
- `run_manifest.json` with:
  - processing run id
  - region
  - data sources used
  - config version
  - code commit if available
  - generation timestamp

This is enough to support static hosting and reproducible reviews.

### Caching and Persistence

The pipeline should not assume remote sources are cheap to re-query on every run.

- scene metadata and derived observation records should be cached locally or in object storage
- generated thumbnails and review artifacts should be persisted and reused across reruns when source scene ids match
- reruns should only fetch or export scenes that are new or invalidated by config changes
- the web viewer should read generated static artifacts, not call GEE directly

### Run Retention Policy

Processing runs are immutable records.

- one run can be marked as the current promoted dataset for a region
- older runs should be retained for comparison and audit
- heavy intermediate artifacts can be archived or garbage-collected by policy once a promoted run exists
- retention policy should distinguish between lightweight metadata, which should be kept, and large imagery artifacts, which may expire

---

## Development Phases

### Phase 1: Feasibility Prototype

Goal:

- determine whether Sentinel-2 contributes useful surf evidence at known spots

Deliverables:

- GEE access verified
- known-spot scene inventory for Lawrencetown and at least 2 additional spots
- exported imagery samples
- observation review sheet
- basic conditions lookup script
- written go / no-go decision

### Phase 2: Nova Scotia Dataset Builder

Goal:

- produce a reproducible ranked Nova Scotia coastline dataset

Deliverables:

- coastline segmentation
- geometry and exposure heuristics
- coarse bathymetry integration
- candidate ranking
- calibration report against known spots
- static output bundle

### Phase 3: Static Web Viewer

Goal:

- browse the Nova Scotia output without rerunning the pipeline

Deliverables:

- map view
- detail panel
- score and evidence explanation
- confirmed vs candidate styling

### Phase 4: Generalized Region Runner

Goal:

- support additional coastlines through a documented developer workflow

Deliverables:

- config or CLI for custom regions
- clearer input validation
- documented prerequisites and expected runtime

### Phase 5: Post-MVP Research and Iteration

Examples:

- live forecast overlay
- user verification
- ML ranking experiments
- higher-resolution imagery experiments

Phase 5 is explicitly off the MVP critical path. None of this work should delay shipping a static Nova Scotia viewer.

---

## Acceptance Criteria

### Phase 1 Acceptance

- at least 3 known spots reviewed
- imagery review process documented
- conditions retrieval working for reviewed scenes
- explicit recommendation: proceed with imagery-assisted product, or pivot to geometry-first

### MVP Acceptance

- Nova Scotia processed end to end from checked-in config
- output includes provenance metadata
- map displays confirmed spots and candidate segments
- detail panel shows explanation for every displayed item
- known spots are usable as calibration references and are not silently mixed with candidates

---

## Risks and Responses

| Risk | Impact | Response |
|------|--------|----------|
| Sentinel-2 is too coarse for reliable surf detection | High | Treat imagery as feasibility-gated evidence, not a guaranteed MVP dependency |
| Cloud cover leaves too few usable observations | High | Sample over long time windows, prefer evidence confidence over false precision |
| Nearshore marine data is too coarse for exact break logic | High | Use it only for broad correlation and wording that matches the data quality |
| Scope grows into a research project before shipping | High | Keep MVP to static NS results plus interpretable heuristics, and keep Phase 5 work off the delivery critical path |
| Known spot seed data is incomplete or noisy | Medium | Use it for calibration, not ground truth for a complex model |
| "Secret spot" concerns create backlash | Medium | Publish coarse candidate segments, add reporting path, avoid exact pin drops by default |

---

## Implementation Notes for the Current Repo

Current repo alignment:

- `pipeline/scripts/01_test_gee_access.py` — scene inventory for a configured spot
- `pipeline/scripts/02_export_sample_images.py` — export Sentinel-2 scenes to Drive for review
- `pipeline/scripts/03_check_conditions.py` — queries both Open-Meteo Marine and Weather APIs, structures output with separate `marine` and `weather` sections per observation
- `pipeline/scripts/04_run_feasibility.py` — orchestrates 01 and 03 across multiple spot configs, produces a combined manifest with processing-run ID and code version
- `pipeline/scripts/05_generate_review_sheet.py` — generates CSV review sheets from manifests for manual imagery labeling
- `pipeline/scripts/_script_utils.py` — shared utilities including `build_run_manifest()` for provenance

Checked-in spot configs:

- `pipeline/configs/lawrencetown.json` (default)
- `pipeline/configs/cow-bay.json`
- `pipeline/configs/martinique-beach.json`

Remaining Phase 1 work:

- authenticate GEE and run the full feasibility pipeline across all three spots
- export and manually review imagery
- fill in observation review sheets
- write the go / no-go feasibility decision

---

## Open Questions

1. Is imagery evidence strong enough to materially improve ranking beyond geometry and bathymetry alone?
2. What is the right public coordinate precision for candidate discoveries?
3. Should the first public release ship only confirmed spots plus candidate segments, with no unnamed spot cards yet?
