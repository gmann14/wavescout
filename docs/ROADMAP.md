# WaveScout Roadmap

*Updated: 2026-04-18*  
*Status: Ordered implementation plan for hardening the MVP*

## How To Use This Doc

This is the execution doc for near-term delivery. It is intentionally concrete. Work should be pulled from top to bottom unless a dependency explicitly says otherwise.

Supporting execution docs:

- [DATA-CONTRACTS.md](DATA-CONTRACTS.md)
- [IMPLEMENTATION-BACKLOG.md](IMPLEMENTATION-BACKLOG.md)
- [IMPLEMENTATION-KICKOFF.md](IMPLEMENTATION-KICKOFF.md)
- [MIGRATION-STRATEGY.md](MIGRATION-STRATEGY.md)
- [UI-STATES.md](UI-STATES.md)
- [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md)
- [REVIEW-GATES.md](REVIEW-GATES.md)
- [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md)
- [TRACEABILITY.md](TRACEABILITY.md)

Every phase follows the same rule:

- `Red`: write the failing tests first
- `Green`: implement the minimum change that makes those tests pass
- `Refactor`: tighten interfaces, remove duplication, improve copy, and document the result

## Mandatory Review Gates

Implementation must pause at these checkpoints for explicit product evaluation:

1. `Gate A`: contract and public-output review
2. `Gate B`: core map and detail-panel UX review
3. `Gate C`: full product consistency review
4. `Gate D`: release readiness review

See [REVIEW-GATES.md](REVIEW-GATES.md) for pass criteria, evaluation questions, and required review records.

## Immediate Next Steps

These are the next actions the repo should take, in order:

1. Add a real pipeline test harness with fixed fixtures and schema assertions.
2. Add frontend unit and route-level smoke tests.
3. Harden contamination handling and evidence-quality flags.
4. Standardize explanation payloads and split `surf potential` from `evidence confidence`.
5. Finish viewer UX states, legends, and accessibility gaps.
6. Add release validation for dataset promotion and deployment.

## Phase 1: Test Harness Baseline

### Goal

Create a minimal but real automated safety net before changing ranking or UX behavior.

### Deliverables

- `pytest` configuration for pipeline tests
- small fixture dataset checked into `tests/fixtures/`
- frontend unit tests in `web/`
- one browser-level smoke test for the happy path

### Red

Add failing tests for:

- `tests/pipeline/test_run_manifest_schema.py`
- `tests/pipeline/test_ranked_output_schema.py`
- `tests/pipeline/test_gallery_manifest_schema.py`
- `web/src/components/__tests__/SpotPanel.test.tsx`
- `web/src/components/__tests__/Nav.test.tsx`
- `web/tests/e2e/map-smoke.spec.ts`

The first assertions should prove:

- manifests include run id, timestamps, and version fields
- ranked output distinguishes confirmed spots from candidate segments
- the spot panel renders loading, success, and missing-data states
- primary navigation and map shell render without runtime errors
- contract validation can assert against [DATA-CONTRACTS.md](DATA-CONTRACTS.md)

### Green

Implement only what is needed to make those tests pass:

- test configuration
- stable fixture readers
- minimal frontend test setup
- a smoke-test command in `web/package.json`

### Refactor

- remove duplicated fixture loading code
- document the test commands in the root and web READMEs
- keep fixtures intentionally small and deterministic

### Exit Criteria

- local contributors can run pipeline and frontend tests with documented commands
- CI can execute those tests without private ad hoc steps
- `Gate A` inputs are ready for review once contract-affecting payload work exists

## Phase 2: Evidence Quality Hardening

### Goal

Make the imagery evidence layer honest enough for product use.

### Deliverables

- contamination masks or explicit quality flags for clouds, snow, shadows, swath-edge issues, and shoreline-sand artifacts
- scene-level and observation-level evidence-quality indicators
- recalibrated foam summaries based on clean observations

### Red

Add failing tests for:

- `tests/pipeline/test_observation_masking.py`
- `tests/pipeline/test_scene_quality_flags.py`
- `tests/pipeline/test_profile_builder_clean_observations.py`

The first assertions should prove:

- contaminated pixels do not count toward foam totals
- low-quality scenes are either excluded or clearly flagged
- swell-profile metrics are derived from clean observations only
- profile eligibility matches [DATA-CONTRACTS.md](DATA-CONTRACTS.md)

### Green

Implement:

- mask handling in the observation pipeline
- per-observation `quality_flag` or equivalent
- recalculation of summary metrics from filtered observations

### Refactor

- consolidate threshold logic into one module
- document each contamination class and how it is handled
- regenerate a known calibration subset and record before/after changes

### Exit Criteria

- known false-positive examples from the validation log are either filtered or clearly downgraded
- the methodology doc and UI can explain the quality flag without hand-waving

## Phase 3: Ranking And Explanation Contract

### Goal

Make every surfaced result explainable in the same language across pipeline, docs, and UI.

### Deliverables

- canonical explanation payload schema
- distinct `surf_potential_score` and `evidence_confidence`
- consistent confirmed/candidate semantics in generated data

### Red

Add failing tests for:

- `tests/pipeline/test_explanation_payload.py`
- `tests/pipeline/test_score_semantics.py`
- `web/src/components/__tests__/ScoreSummary.test.tsx`

The first assertions should prove:

- every ranked item has summary, highlights, caveats, and provenance
- score semantics are stable across confirmed spots and candidates
- the UI labels low-confidence cases correctly
- publication status is independent from verification status

### Green

Implement:

- a shared explanation builder
- explicit score fields in generated artifacts
- UI rendering for summary, highlights, caveats, and provenance

### Refactor

- remove legacy ambiguous `confidence` usage where it mixes verification state and evidence quality
- align docs and copy with the new field names

### Exit Criteria

- a user can inspect any item and understand why it appears in the product
- no core doc uses contradictory score language
- stop here for `Gate A` before further viewer work if payload semantics changed

## Phase 4: Viewer UX Hardening

### Goal

Finish the product-facing experience so it behaves like a release candidate rather than an internal viewer.

### Deliverables

- map legend and state explanations
- detail-panel empty and error states
- atlas orientation aids
- compare-page date clarity
- keyboard/focus/accessibility pass

### Red

Add failing tests for:

- `web/src/components/__tests__/MapLegend.test.tsx`
- `web/src/components/__tests__/DetailPanelStates.test.tsx`
- `web/src/components/__tests__/CompareView.test.tsx`
- `web/tests/e2e/navigation.spec.ts`

The first assertions should prove:

- users can tell confirmed spots from candidate segments without relying on color alone
- empty or missing gallery states are explicit
- compare results never silently mix dates
- keyboard users can open and close the panel and move through nav links
- page behavior matches [UI-STATES.md](UI-STATES.md)

### Green

Implement:

- legend and helper copy
- state-specific UI for missing imagery and sparse evidence
- mobile-safe panel behavior
- compare-page scene-date labeling

### Refactor

- simplify any duplicated state rendering logic
- make loading and error components reusable
- tighten copy to match the spec vocabulary exactly

### Exit Criteria

- the MVP core flows are understandable without the author narrating them
- basic accessibility regressions are covered by tests
- stop here for `Gate B` after the home-page flows are usable
- stop again for `Gate C` once atlas, compare, and content routes match the same semantics

## Phase 5: Release And Promotion Discipline

### Goal

Make dataset promotion and deployment auditable and repeatable.

### Deliverables

- documented promoted-dataset workflow
- release checklist
- deploy verification steps
- smoke check against the promoted static dataset

### Red

Add failing tests or validation scripts for:

- run-manifest completeness
- promoted-dataset folder structure
- web build against the promoted dataset
- public-output policy compliance
- traceability coverage for release-blocking requirements

### Green

Implement:

- a documented promotion command or script
- release notes template tied to the promoted run

### Refactor

- remove manual release ambiguity where a script or checklist can enforce the rule
- ensure review records are linked from the release artifact or PR

### Exit Criteria

- promotion and deployment can be executed from documented steps
- release evidence is durable enough for `Gate D`
- stop here for `Gate D` before any release-ready claim
- build validation in CI
- release gating against [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md)
- payload policy checks against [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md)

### Refactor

- remove undocumented manual release steps
- ensure deployment docs do not assume infrastructure that has not been configured

### Exit Criteria

- a new promoted dataset can be reproduced, validated, and deployed by following docs alone

## Deferred Research

These are valid research tracks, but they are not on the MVP critical path:

- swell-line detection
- break-type classification
- temporal consistency scoring beyond the current profile model
- user-adjustable weighting
- community verification systems
- forecast overlays

They should stay behind MVP hardening unless they directly unblock a documented release criterion.
