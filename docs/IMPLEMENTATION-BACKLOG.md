# WaveScout Implementation Backlog

*Updated: 2026-04-17*  
*Status: Ordered workboard for the first implementation cycle*

## Purpose

This document turns the roadmap into ticket-sized execution units with explicit dependencies and acceptance criteria.

Use this with:

- [ROADMAP.md](ROADMAP.md)
- [DATA-CONTRACTS.md](DATA-CONTRACTS.md)
- [UI-STATES.md](UI-STATES.md)
- [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md)
- [MIGRATION-STRATEGY.md](MIGRATION-STRATEGY.md)

## Global Rules

- do not start feature work before `WS-01` and `WS-02`
- do not remove legacy payload fields before `WS-06`
- do not promote a dataset before `WS-09`
- do not merge implementation that contradicts the spec set without updating the docs first

## Suggested PR Order

1. `WS-01` pipeline test foundation
2. `WS-02` frontend test foundation
3. `WS-03` contract validation and dataset manifest
4. `WS-04` payload normalization in build scripts
5. `WS-05` publication filtering and coarse-public enforcement
6. `WS-06` web app migration to normalized fields
7. `WS-07` viewer state completion
8. `WS-08` contamination and quality-state hardening
9. `WS-09` release gating and CI expansion

## Tickets

### `WS-01` Pipeline Test Foundation

Priority:

- P0

Depends on:

- none

Scope:

- add `pytest` configuration
- add `tests/pipeline/`
- add `tests/fixtures/`
- add first schema-oriented pipeline tests from [ROADMAP.md](ROADMAP.md)

Acceptance criteria:

- `pytest` runs locally
- fixture data is small and deterministic
- run manifest and ranked output schema tests fail for the right reasons or pass against intentionally prepared fixtures

Likely files:

- `pytest.ini`
- `tests/pipeline/test_run_manifest_schema.py`
- `tests/pipeline/test_ranked_output_schema.py`
- `tests/pipeline/test_gallery_manifest_schema.py`

### `WS-02` Frontend Test Foundation

Priority:

- P0

Depends on:

- none

Scope:

- choose frontend test runner
- choose e2e runner
- add basic setup
- add first component and route smoke tests

Acceptance criteria:

- `pnpm test` runs locally
- `pnpm test:e2e` has a documented smoke target
- first tests cover nav and spot panel shell behavior

Likely files:

- `web/package.json`
- `web/src/components/__tests__/Nav.test.tsx`
- `web/src/components/__tests__/SpotPanel.test.tsx`
- `web/tests/e2e/map-smoke.spec.ts`

### `WS-03` Contract Validation And Dataset Manifest

Priority:

- P0

Depends on:

- `WS-01`

Scope:

- define generated `dataset-manifest.json`
- add validators for required public artifacts
- assert normalized contract presence during build validation

Acceptance criteria:

- the repo can validate whether a dataset matches [DATA-CONTRACTS.md](DATA-CONTRACTS.md)
- missing required artifacts fail loudly
- dataset manifest includes provenance fields

Likely files:

- `pipeline/scripts/build_web_data.py`
- `pipeline/scripts/build_atlas_web_data.py`
- validation helpers under `pipeline/scripts/` or `pipeline/lib/`

### `WS-04` Payload Normalization In Build Scripts

Priority:

- P0

Depends on:

- `WS-03`

Scope:

- emit normalized public payload fields
- preserve legacy fields temporarily per [MIGRATION-STRATEGY.md](MIGRATION-STRATEGY.md)
- propagate explanation/provenance/publication fields into web payloads

Acceptance criteria:

- build scripts emit `surf_potential_score`
- build scripts emit `evidence_confidence_level` and label
- build scripts emit `verification_status` and `publication_status`
- selectable public payloads emit `explanation`

Likely files:

- `pipeline/scripts/build_web_data.py`
- `pipeline/scripts/build_atlas_web_data.py`

### `WS-05` Publication Filtering And Coarse-Public Enforcement

Priority:

- P0

Depends on:

- `WS-04`

Scope:

- exclude `internal_only` entities from public dataset
- coarsen coordinates for `public_coarse`
- ensure public candidates are unnamed in public outputs

Acceptance criteria:

- local/private references do not leak into the public web payload
- `public_coarse` entities comply with [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md)
- policy validation exists

Likely files:

- `pipeline/scripts/build_web_data.py`
- policy validation tests

### `WS-06` Web App Migration To Normalized Fields

Priority:

- P0

Depends on:

- `WS-04`

Scope:

- migrate data types and loaders
- read normalized fields first, then legacy fallback during migration window
- replace UI use of ambiguous `confidence`

Acceptance criteria:

- `Map`, `Atlas`, `Compare`, and detail surfaces render from normalized payloads
- legacy fallback is documented and temporary
- no new UI code depends on legacy `confidence`

Likely files:

- `web/src/types.ts`
- `web/src/lib/data.ts`
- `web/src/components/MapView.tsx`
- `web/src/components/SpotPanel.tsx`
- atlas and compare components as needed

### `WS-07` Viewer State Completion

Priority:

- P1

Depends on:

- `WS-02`
- `WS-06`

Scope:

- implement [UI-STATES.md](UI-STATES.md)
- add legend and state-specific copy
- add sparse-compare, no-gallery, no-profile, and degraded-evidence states

Acceptance criteria:

- core viewer states match the state matrix
- tests cover state rendering
- keyboard/focus behavior works on the main flows

### `WS-08` Contamination And Quality-State Hardening

Priority:

- P1

Depends on:

- `WS-01`
- `WS-03`

Scope:

- implement contamination handling
- calculate `quality_status`
- align gallery/profile eligibility with [DATA-CONTRACTS.md](DATA-CONTRACTS.md)

Acceptance criteria:

- false-positive examples from [SPOT-VALIDATION-LOG.md](SPOT-VALIDATION-LOG.md) are downgraded or filtered
- profile eligibility is deterministic
- quality thresholds are enforced in generated payloads

### `WS-09` Release Gating And CI Expansion

Priority:

- P1

Depends on:

- `WS-01`
- `WS-02`
- `WS-03`
- `WS-05`
- `WS-07`

Scope:

- expand CI beyond current web build/typecheck
- add dataset validation and policy checks
- automate release gate checks

Acceptance criteria:

- CI can fail on contract, policy, or test regressions
- release checklist can be executed from docs alone
- dataset promotion has an explicit validation path

## Definition Of Ready

A ticket is ready to start only if:

- its dependencies above are complete
- the acceptance criteria are clear
- the target docs are identified
- the expected output files or UI surfaces are known

## Definition Of Done

A ticket is done only if:

- code and tests are merged
- touched docs still match reality
- no new ambiguous field names or state semantics were introduced
