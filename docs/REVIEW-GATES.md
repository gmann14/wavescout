# WaveScout Review Gates

*Updated: 2026-04-18*  
*Status: Required evaluation checkpoints during implementation*

## Purpose

This document defines the planned moments where implementation must pause for product evaluation.

These are not optional demos. They are decision points used to determine whether the work is acceptable before the next implementation slice begins.

If a gate fails, the next phase does not start until the blocking issues are resolved or the spec is explicitly updated.

## How To Use This Doc

At each gate, evaluate only these four dimensions:

- correctness
- clarity
- UX quality
- scope discipline

Each gate should produce one of three outcomes:

- `pass`: continue to the next planned phase
- `pass with follow-ups`: continue, but log explicit cleanup items
- `fail`: stop the next phase and fix the blocking issues first

## Gate A: Contract And Public Output

### When

Run this gate after the contract-validation and payload-migration work is in place.

In roadmap terms, this is the stop point after:

- Phase 1
- Phase 3 contract implementation work that changes exported payload shape

### What To Review

- [DATA-CONTRACTS.md](DATA-CONTRACTS.md)
- [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md)
- generated `web/public/data/*`
- contract-validation test results

### Pass Criteria

- no `internal_only` entities leak into public payloads
- normalized score and evidence fields are present and stable
- explanation payloads are present where the contract requires them
- public artifacts match the documented dataset layout
- no release-blocking contract ambiguity remains

### Evaluation Questions

- Are the payloads correct enough that frontend work can proceed without schema churn?
- Does the public dataset expose only what policy allows?
- Would a new engineer understand the payload without tribal knowledge?

## Gate B: Core UX And UI Quality

### When

Run this gate after the map, spot panel, and required core UI states are implemented.

In roadmap terms, this is the stop point after the home-page UX work in:

- Phase 4 for map and detail-panel behavior

### What To Review

- [UI-STATES.md](UI-STATES.md)
- [SPEC.md](SPEC.md)
- home page on desktop and mobile
- loading, empty, partial-data, low-confidence, and error states

### Pass Criteria

- the map and detail panel are understandable without narration
- labels, legends, and state copy match the spec vocabulary
- low-confidence and sparse-evidence cases are communicated clearly
- mobile behavior is acceptable and not merely functional
- obvious accessibility failures are absent

### Evaluation Questions

- Can a user understand what they are looking at in under a minute?
- Are uncertainty and evidence quality obvious without digging?
- Does the product feel intentional, not merely wired up?

## Gate C: Cross-Product Consistency

### When

Run this gate after atlas, compare, and supporting content routes are brought onto the normalized contract and state model.

In roadmap terms, this is the stop point after:

- remaining Phase 4 viewer-hardening work
- any follow-up route migrations needed for consistency

### What To Review

- map
- atlas
- compare
- methodology and about pages
- shared copy, legends, and state behavior

### Pass Criteria

- the same concepts mean the same thing in every route
- no route still depends on contradictory legacy semantics
- compare and atlas states are explicit and test-backed
- content pages align with actual product behavior

### Evaluation Questions

- Does the product feel like one system rather than separate experiments?
- Are there any pages still telling a different story about scores or certainty?
- Would a first-time user encounter contradictory explanations between routes?

## Gate D: Release Readiness

### When

Run this gate before any release-ready, public-demo, or promoted-dataset claim.

This is the final stop point after:

- Phase 5 release and promotion work

### What To Review

- [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md)
- [TRACEABILITY.md](TRACEABILITY.md)
- final generated dataset
- full test and manual QA results

### Pass Criteria

- release checklist is complete
- blocking traceability gaps are closed
- promotion artifacts are reproducible and auditable
- policy, contract, and UI-state requirements all pass together

### Evaluation Questions

- Is this actually ready to show externally without apology?
- Can the release be reproduced and defended from artifacts alone?
- Are the remaining issues truly non-blocking?

## Review Record

For each gate, record:

- gate name
- date
- reviewer
- outcome
- blocking issues
- approved follow-ups

This record can live in the PR description, release notes draft, or an explicit review issue, but it must exist somewhere durable.
