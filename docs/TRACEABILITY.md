# WaveScout Traceability Matrix

*Updated: 2026-04-17*  
*Status: Requirement-to-test and requirement-to-release mapping*

## Purpose

This document maps the core product requirements to the planned test surfaces and release gates. A requirement without a planned verification path should be treated as incomplete.

| ID | Requirement | Source | Planned Verification | Release Gate |
|---|---|---|---|---|
| TR-01 | MVP is Nova Scotia-only and static-data-first | [SPEC.md](SPEC.md) | route smoke tests, dataset manifest validation | release checklist docs sync |
| TR-02 | map exposes `Map`, `Atlas`, `Compare`, `How It Works`, `About` | [SPEC.md](SPEC.md) | `Nav.test.tsx`, navigation e2e | manual QA nav |
| TR-03 | map has loading, config-error, data-error, and empty states | [SPEC.md](SPEC.md), [UI-STATES.md](UI-STATES.md) | map shell tests, e2e smoke | manual QA map |
| TR-04 | confirmed and candidate states are visually distinct without color alone | [SPEC.md](SPEC.md), [UI-STATES.md](UI-STATES.md) | `MapLegend.test.tsx`, navigation e2e | manual QA map |
| TR-05 | detail panel exposes score, confidence, signals, caveats, and provenance | [SPEC.md](SPEC.md), [DATA-CONTRACTS.md](DATA-CONTRACTS.md) | `SpotPanel.test.tsx`, `ScoreSummary.test.tsx`, payload schema tests | contract checks |
| TR-06 | low-confidence results are explicitly labeled | [SPEC.md](SPEC.md), [UI-STATES.md](UI-STATES.md) | score-summary/component tests | manual QA detail |
| TR-07 | compare rows never mix acquisition dates | [SPEC.md](SPEC.md), [UI-STATES.md](UI-STATES.md) | `CompareView.test.tsx`, compare e2e | manual QA compare |
| TR-08 | sparse compare dates are flagged when forced by query param | [UI-STATES.md](UI-STATES.md), [DATA-CONTRACTS.md](DATA-CONTRACTS.md) | compare component tests | manual QA compare |
| TR-09 | methodology copy does not imply current conditions or exact tide knowledge | [SPEC.md](SPEC.md), [METHODOLOGY.md](METHODOLOGY.md) | doc review, content snapshots | documentation sync |
| TR-10 | product separates `surf_potential_score` from `evidence_confidence` | [SPEC.md](SPEC.md), [DATA-CONTRACTS.md](DATA-CONTRACTS.md) | `test_score_semantics.py`, UI score tests | contract checks |
| TR-11 | selectable public entities include explanation payload | [SPEC.md](SPEC.md), [DATA-CONTRACTS.md](DATA-CONTRACTS.md) | `test_explanation_payload.py`, schema tests | artifact checks |
| TR-12 | context-only layers are exempt from full explanation payload | [DATA-CONTRACTS.md](DATA-CONTRACTS.md) | schema tests on `segments-all.json` | contract checks |
| TR-13 | swell-profile summary shown only above eligibility threshold | [DATA-CONTRACTS.md](DATA-CONTRACTS.md) | `test_profile_builder_clean_observations.py`, panel-state tests | manual QA detail |
| TR-14 | contamination handling downgrades or excludes bad scenes | [SPEC.md](SPEC.md), [ROADMAP.md](ROADMAP.md) | masking tests, scene-quality tests | policy + QA review |
| TR-15 | public dataset includes required provenance fields | [SPEC.md](SPEC.md), [DATA-CONTRACTS.md](DATA-CONTRACTS.md) | manifest schema tests | provenance checks |
| TR-16 | processing run promotion is explicit and auditable | [SPEC.md](SPEC.md), [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md) | promotion validation script | sign-off |
| TR-17 | local/private references are not exposed publicly by default | [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md) | payload policy checks | policy review |
| TR-18 | public candidates are coarse-public only | [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md), [DATA-CONTRACTS.md](DATA-CONTRACTS.md) | payload precision checks | policy review |
| TR-19 | keyboard and focus accessibility exists on core interactions | [SPEC.md](SPEC.md), [UI-STATES.md](UI-STATES.md) | navigation e2e, component tests | manual QA accessibility |
| TR-20 | release docs and implementation stay synchronized | [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md) | release review | documentation sync |
