# WaveScout Migration Strategy

*Updated: 2026-04-17*  
*Status: Chosen migration plan for moving from current payloads to the normalized public contract*

## Purpose

The current payloads and UI use legacy fields such as `confidence`. The new contract set requires normalized score, verification, publication, and quality semantics.

This document chooses the migration strategy so implementation does not thrash.

## Decision

Use a two-step backward-compatible migration.

### Step A: Dual-Write, Dual-Read

Pipeline/build behavior:

- emit normalized fields required by [DATA-CONTRACTS.md](DATA-CONTRACTS.md)
- keep legacy fields temporarily where needed for compatibility

Web behavior:

- read normalized fields first
- fall back to legacy fields only where the normalized field is absent

### Step B: Legacy Removal

After validators, UI migration, and tests are green:

- remove legacy public fields
- remove fallback reads from the web app
- fail builds that still depend on legacy public fields

## Why This Strategy

This is safer than a one-shot cutover because:

- current generated payloads are already consumed by the web app
- multiple files need to change together
- contract validators can be introduced before field removal

This is stricter than indefinite compatibility because:

- legacy fields remain a documented temporary bridge
- removal is an explicit deliverable, not a “later maybe”

## Migration Rules

- new code must write normalized fields
- new UI code must prefer normalized fields
- no new code may introduce additional legacy field names
- legacy `confidence` must not appear in new docs or new UI copy

## Field Migration Map

| Current | Target | Notes |
|---|---|---|
| `score` | `surf_potential_score` | public score field |
| `confidence` | `evidence_confidence_level` plus label | do not reuse for verification/publication |
| spot `confidence` string | split into `verification_status`, `publication_status`, `evidence_confidence_*` | current meaning is mixed and must be untangled |
| implicit public spots | explicit `publication_status` | required for policy compliance |
| missing explanation in web payloads | `explanation` object | propagate from pipeline or normalize in build step |

## Exit Conditions

The migration is complete only when all are true:

- public payloads conform to [DATA-CONTRACTS.md](DATA-CONTRACTS.md)
- the web app no longer needs legacy fallback reads
- release checks fail if legacy public fields remain

## Non-Goals

- no attempt to preserve exact old field semantics forever
- no attempt to maintain undocumented public payload formats
