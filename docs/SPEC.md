# WaveScout Product Spec

*Updated: 2026-04-17*  
*Status: Source of truth for MVP scope, UX/UI requirements, and release criteria*

## Purpose

This document defines the WaveScout MVP and near-term product requirements. It is intentionally stricter than brainstorm docs. If a statement here conflicts with a vision or research doc, this document wins.

Normative companion docs:

- [DATA-CONTRACTS.md](DATA-CONTRACTS.md)
- [UI-STATES.md](UI-STATES.md)
- [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md)
- [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md)
- [TRACEABILITY.md](TRACEABILITY.md)

## Current State

The repo already contains:

- a Nova Scotia-oriented processing pipeline with scripts through segmentation, geometry scoring, foam detection, swell profiling, ranking, and static web-data export
- a static Next.js viewer with a primary discovery `Map`, `Compare`, `How It Works`, and `About` pages, plus section-analysis support layered into the map workflow
- manual validation notes showing that Sentinel-2 imagery can contribute useful evidence at some known spots

The repo does not yet have MVP-quality guarantees for:

- contamination handling across clouds, snow, shadows, swath edges, and low-tide sand
- consistent score semantics across all docs and UI surfaces
- automated regression coverage for pipeline outputs and viewer behavior
- clear release-grade UX states for loading, empty, error, and low-confidence evidence

## Product Thesis

Surf discovery is under-served. Existing surf tools are strongest once a break is already known. WaveScout fills the earlier step: identify coastline segments worth checking, show the evidence, and make uncertainty explicit.

WaveScout is:

- an evidence-driven discovery tool
- static-data-first
- Nova Scotia-first
- provenance-oriented

WaveScout is not:

- a live surf forecast
- a guarantee of safety, access, or quality
- a secret-spot precision pin-dropper

## Primary User Jobs

### Local Explorer

Needs to answer:

- what unfamiliar coastline segments are worth checking
- why the system thinks they are promising
- how much evidence is behind that claim

### Traveling Researcher

Needs to answer:

- which known or candidate locations match the swell context they care about
- how exposed each area is
- what the satellite record actually shows

### Technical Reviewer

Needs to answer:

- what data sources were used
- what run produced the result
- how reproducible the score and images are

## MVP Definition

The MVP is a static Nova Scotia surf-discovery viewer built from precomputed data.

### MVP Includes

1. Ranked Nova Scotia coastline outputs with provenance.
2. A map view for browsing confirmed spots and candidate segments.
3. A detail experience that explains score, evidence, and caveats.
4. A section-analysis overlay for broader coastline browsing inside the main map workflow.
5. A compare view for same-date cross-spot inspection.
6. Methodology and about pages written for non-specialist users.

### MVP Excludes

- live forecast recommendations
- user-triggered reprocessing from the browser
- crowdsourced moderation systems
- exact tide claims
- community spot submissions as a release dependency
- global self-serve processing

## Product Vocabulary

These terms must be used consistently across docs and UI:

- `confirmed spot`: a known surf location included as a reference entry
- `candidate segment`: a coastline segment or grouped section that scores as promising but is not publicly confirmed
- `atlas section`: a larger coastline browsing unit used by the atlas
- `surf potential score`: how promising the location looks
- `evidence confidence`: how strong the supporting data is
- `observation`: one scene-location pairing with derived evidence

Do not collapse `surf potential score` and `evidence confidence` into one unlabeled confidence number.

Additional required fields:

- `verification_status`: whether the entity is confirmed, candidate, or rejected
- `publication_status`: whether the entity is `public_named`, `public_coarse`, or `internal_only`

These concepts must stay separate.

## UX/UI Requirements

### Global Navigation

The global nav must expose:

- `Map`
- `Compare`
- `How It Works`
- `About`

Requirements:

- the active route is visually distinct
- navigation works on desktop and mobile
- the region label remains obvious: Nova Scotia only for MVP

### Map Page

Primary user goal: quickly find promising areas and inspect why they rank highly.

Required behavior:

- default viewport loads Nova Scotia without requiring user input
- confirmed spots and candidate segments use clearly different visual treatments
- the legend or nearby copy explains what each color/state means
- selecting a feature opens a detail panel without losing map context
- map interactions must remain usable with the detail panel open on mobile and desktop
- the main `Map` candidate surface is stricter than the optional section-analysis overlay and may hide low-quality or sheltered candidates that remain visible in broader coastline browsing

Required states:

- loading state while map data is being fetched
- missing-token state with a clear operator-facing error
- empty-data state if a dataset is unavailable
- low-confidence presentation for geometry-only or sparse-evidence results

Required candidate-display policy:

- the main `Map` page must only display candidates that are eligible for public lead browsing
- rivers, estuaries, harbours, and sheltered inner bays must not be treated as normal surf candidates on the main `Map`
- broader section analysis may remain available as an overlay, but it must not imply that every section is a public surf lead
- candidate display eligibility must be driven by generated data, not undocumented UI-only heuristics

Non-interactive context-only layers are allowed for map density and orientation, but they are exempt from the full detail payload requirement as long as they are not selectable.

### Detail Panel

The detail panel is a core product surface. It must answer four questions in under 15 seconds:

1. What is this location?
2. Why is it ranked this way?
3. What evidence supports the ranking?
4. What should the user be cautious about?

Required sections:

- label and type: confirmed spot or candidate segment
- short summary in plain English
- surf potential score
- evidence confidence
- key signals
- key caveats
- satellite gallery or explicit `no gallery available` state
- swell-response summary only when the entity is profile-eligible
- provenance reference to the dataset or run

The panel must never imply certainty when evidence is weak.

If gallery scenes are suppressed for quality reasons, the panel must state that the imagery record exists but is not currently publishable.

The public gallery remains strict by default. Denser internal reference banks may exist for research, but they must remain separate from the promoted public gallery contract.

`when enough observations exist` is now defined by [DATA-CONTRACTS.md](DATA-CONTRACTS.md):

- at least `30` clean observations
- at least `3` non-empty swell bins
- completed profile build status

### Section Analysis Overlay

Primary user goal: switch from spot-first browsing into broader coastline review without leaving the main discovery map.

Requirements:

- section boxes are visually distinct and selectable when analysis mode is enabled
- the section panel summarizes section-level context before showing imagery
- the UI must explain that section boxes are browsing aids, not a list of confirmed breaks
- users can enable or disable section analysis without losing map context

### Compare Page

Primary user goal: see how different spots respond to the same satellite pass.

Requirements:

- date selection is obvious
- the page explains why same-date comparison matters
- missing imagery or incomplete condition data is called out directly
- same-date results must not mix scenes from different acquisitions

Default compare inclusion is now defined as dates with at least `3` unique public spots with compare-eligible scenes. Direct date links may show sparser sets, but they must be labeled as sparse comparison.

### How It Works Page

This page is user education, not an internal notebook dump.

Requirements:

- explain the method in plain language
- explain what the system can and cannot infer
- define contamination and uncertainty clearly
- avoid hardcoding fragile numeric claims unless they are intentionally versioned snapshots

### About Page

Requirements:

- explain the mission and release boundaries
- emphasize safety, access, and uncertainty
- avoid overclaiming what the system can prove

## UX Copy Rules

UI copy must:

- prefer `shows evidence of breaking waves` over `is a great wave`
- prefer `works best in observed scenes around` over `works at`
- prefer `coarse sea-level context` over `tide`
- use `candidate` for unverified discoveries

UI copy must not:

- imply that a candidate is definitely surfable
- imply current conditions unless the view is explicitly historical
- imply exact local tide knowledge from coarse data

## Accessibility Requirements

MVP is not complete without these:

- all interactive controls reachable by keyboard
- visible focus states
- non-color cues for confirmed vs candidate vs low-confidence states
- alt text or accessible labels for gallery controls and map-adjacent actions
- text contrast that remains readable on the dark map-driven UI

## Data and Scoring Requirements

### Data Sources

MVP relies on:

- Sentinel-2 imagery via Google Earth Engine
- Open-Meteo marine and weather context
- coarse bathymetry such as GEBCO
- coastline and road geometry
- a checked-in known-spot reference set

### Data Constraints

The product must explicitly acknowledge:

- 10 m imagery is coarse
- nearshore marine data is approximate
- cloud and surface contamination are material risks
- candidate output must be less precise than confirmed public spot output where sensitivity matters

### Scoring Contract

Every displayed location must expose:

- surf potential score
- evidence confidence
- score components or explanation highlights
- caveats

Every selectable public entity must also expose:

- verification status
- publication status
- provenance

At minimum the explanation payload must support:

- summary
- score components
- highlights
- caveats
- provenance fields

## Pipeline Requirements

### Output Bundle

The portable output bundle for the web app must include:

- `dataset-manifest.json`
- ranked location GeoJSON or equivalent JSON payload
- detail payloads for confirmed spots and candidate segments
- gallery metadata when imagery exists
- run manifest with code version, config version, generation time, and source metadata

### Provenance

Each promoted dataset must be traceable to:

- a processing run id
- input config
- code revision, or the literal string `unknown`
- generation timestamp
- source dataset versions where practical

### Promotion Model

Processing runs are immutable records. Promotion to `current dataset` must be explicit. Rebuilds must not silently overwrite the promoted dataset without a new manifest.

Public entities must also satisfy [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md). In particular:

- local/private references default to `internal_only`
- candidates default to `public_coarse`
- public named output is not implied by confirmation alone

## Release Criteria

MVP is ready only when all of the following are true:

1. The promoted Nova Scotia dataset can be reproduced from checked-in configs and documented commands.
2. Every selectable public map or atlas item has an explanation payload.
3. The UI distinguishes confirmed spots from candidate segments without relying on color alone.
4. Loading, empty, and error states exist for the map, detail panel, atlas, and compare pages.
5. Methodology, README, and product copy agree on scope and limitations.
6. The payloads conform to [DATA-CONTRACTS.md](DATA-CONTRACTS.md).
7. Public output conforms to [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md).
8. The release gate in [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md) is complete.
9. The automated test suite described in [ROADMAP.md](ROADMAP.md) exists and passes on the release branch.

## Near-Term Delivery Priorities

The next delivery work is:

1. establish a real test harness for pipeline and web
2. harden contamination masking and evidence-quality flags
3. standardize score semantics and explanation payloads
4. polish viewer UX states and accessibility
5. formalize release promotion and deploy checks

The ordered implementation plan, including red/green TDD stages, lives in [ROADMAP.md](ROADMAP.md).
