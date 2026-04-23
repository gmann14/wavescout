# WaveScout Review Records

Durable review log for the implementation gates defined in [REVIEW-GATES.md](REVIEW-GATES.md).

## Gate A

- Gate: `Gate A`
- Date: `2026-04-20`
- Reviewer: `Codex`
- Outcome: `pass`
- Blocking issues: none
- Approved follow-ups: none
- Evidence:
  - strict public dataset validation
  - normalized payload contracts in [DATA-CONTRACTS.md](DATA-CONTRACTS.md)
  - generated public dataset under `web/public/data/`

## Gate B

- Gate: `Gate B`
- Date: `2026-04-20`
- Reviewer: `Graham + Codex`
- Outcome: `pass with follow-ups`
- Blocking issues: none
- Approved follow-ups:
  - continue improving private/reference imagery density without weakening the public gallery
  - continue tightening candidate quality on the main `Map` surface as more validation data comes in
- Evidence:
  - manual browser review in this implementation thread
  - core map/detail fixes for blank map, legend clarity, focus behavior, panel states, and gallery suppression messaging
  - passing component and browser smoke tests

## Gate C

- Gate: `Gate C`
- Date: `2026-04-20`
- Reviewer: `Codex`
- Outcome: `pass with follow-ups`
- Blocking issues: none
- Approved follow-ups:
  - keep expanding stronger same-semantics regression coverage as new spots are promoted into the strict calibration set
- Evidence:
  - normalized contract usage across `Map`, `Atlas`, `Compare`, `How It Works`, and `About`
  - route-level browser smoke coverage
  - explicit atlas/compare/content state handling from [UI-STATES.md](UI-STATES.md)

## Gate D

- Gate: `Gate D`
- Date: `2026-04-20`
- Reviewer: `Codex`
- Outcome: `pass with follow-ups`
- Blocking issues: none
- Approved follow-ups:
  - run `pipeline/scripts/promote_public_dataset.py` with explicit named reviewers when you want to mark the current dataset as promoted
- Evidence:
  - green release-readiness report at `pipeline/data/manifests/release_readiness_report.json`
  - strict dataset validation including atlas artifacts
  - release-check and promotion scripts
  - expanded CI workflow covering release-readiness plus browser smoke

## Gate C (re-run 2026-04-23)

- Gate: `Gate C`
- Date: `2026-04-23`
- Reviewer: `Claude`
- Outcome: `pass with follow-ups`
- Blocking issues: none
- Approved follow-ups:
  - `web/src/app/about/page.tsx:62-69` — About page "Pipeline" Step 2 still names "Detect Foam via NIR" and Step 3 leads with "correlating foam detection with swell conditions". Every other route demotes NIR/foam to exploratory telemetry (SpotPanel.tsx:240-271 "Exploratory detection telemetry"; CompareView.tsx:331-370 collapsed "Detection details"; methodology.md frames NIR as one of several evidence layers). Rewrite these two steps so foam/NIR are framed as one supporting evidence layer, not the headline method — consistent with `methodology.md` and `SPEC.md §vocabulary`.
  - `web/src/components/MapView.tsx:39-42` (`getConfidenceBadge`) — map popup renders evidence as "Satellite verified / Partial data / Geometry only" while SpotPanel renders the same `evidence_confidence_label` via `formatEvidenceLabel` as "High evidence / Moderate evidence / Low evidence / No evidence" (`web/src/lib/spotData.ts:228`). Same underlying `evidence_confidence_level`, two divergent public vocabularies on routes that hand off to each other. Unify to the `formatEvidenceLabel` strings (or explicitly document the map's operator-facing variant).
  - `web/src/components/AtlasMap.tsx` is dead code (not mounted — `/atlas` redirects to `/?analysis=atlas` in `web/src/app/atlas/page.tsx`). It carries its own score color thresholds and legend copy; delete or gate it so it cannot drift against `MapView`.
- Evidence:
  - canonical vocabulary verified against `docs/DATA-CONTRACTS.md:64-88` and `docs/SPEC.md:101-114` — `surf_potential_score`, `evidence_confidence_level/label`, `verification_status`, `publication_status`.
  - score/confidence parity enforced in `SpotPanel.tsx:174-211` (peer `tier-hero` tiles with `hero-number` values) and locked by `SpotPanel.test.tsx:162-185`.
  - NIR/foam demotion: `CompareView.tsx:331-370` keeps detection details collapsed by default; `SpotPanel.tsx:240-271` reframes foam as "Exploratory detection telemetry"; `CompareView.test.tsx:198-222` asserts no "NIR / foam / %" surface in the default compare view.
  - sparse-compare banner in `CompareView.tsx:270-277` matches `UI-STATES.md §compare-ready-sparse-date`; `CompareView.test.tsx:132-170` covers both sparse and no-match.
  - shared design tokens in `web/src/app/globals.css:4-50` (warm-bone palette, serif `font-display`, mono `font-readout`, overline treatment) are applied on every route — home overline `Nova Scotia · Coastline atlas` (`MapView.tsx:627`), compare `Compare · Same acquisition date`, about `About · Nova Scotia`, methodology `Methodology · Field note`.
  - candidate-vs-confirmed consistent across surfaces: `MapLegend.tsx:33-44` (Named spots / Candidate segments / Context coastline), `SpotPanel.tsx:131-148` (confirmed/candidate badges), `AtlasSectionPanel.tsx:259` ("browsing units, not confirmed breaks").
  - tests green: `npx vitest run` → 5 files, 16/16 passing; `npx tsc --noEmit` → clean.

## Gate D (re-run 2026-04-23)

- Gate: `Gate D`
- Date: `2026-04-23`
- Reviewer: `Claude`
- Outcome: `fail`
- Blocking issues:
  - `web/public/data/atlas/sections.json` is missing. `pipeline/scripts/check_release_readiness.py --skip-commands` reports `artifacts.atlas_sections_exists failed` and `ready: false` in `pipeline/data/manifests/release_readiness_report.json` (regenerated 2026-04-23T21:45:35Z). This trips the `RELEASE-CHECKLIST.md` artifact check (line 29) and the stop condition "promoted dataset is missing a required artifact from DATA-CONTRACTS.md" (line 16).
  - Source GeoJSON `pipeline/data/atlas/ns_atlas_sections.geojson` consumed by `pipeline/scripts/build_atlas_web_data.py` is not in the worktree or in git history, so the artifact cannot be regenerated from the current repo state. Running the builder emits `sections: no atlas data found. Run script 17 first.` and `_public_dataset.validate_public_dataset` raises `dataset-manifest artifacts missing required keys: ['atlas_sections']`.
  - `web/public/data/dataset-manifest.json` (regenerated 2026-04-23T21:46:06Z) no longer advertises an `atlas_sections` artifact, so the dataset manifest itself now fails the provenance/contract checks that the 2026-04-20 Gate D relied on.
- Approved follow-ups:
  - Restore or regenerate `pipeline/data/atlas/ns_atlas_sections.geojson` (tiling script 17), rerun `pipeline/scripts/build_atlas_web_data.py`, then rerun `check_release_readiness.py` end-to-end (without `--skip-commands`) and record a fresh green report before any external release claim.
  - Decide whether `atlas/sections.json` should be committed (with provenance) or whether the upstream GeoJSON should be tracked so CI can reproduce it — today neither is true, which is why CI's `release-readiness` job would fail on `main`.
- Evidence:
  - `pipeline/data/manifests/release_readiness_report.json` → `generated_at_utc: 2026-04-23T21:45:35.049467+00:00`, `ready: false`, `failures: ["artifacts.atlas_sections_exists failed"]`.
  - Non-gating checks pass from the design-pass worktree (HEAD `2828180`): `cd web && npx vitest run` → 5 files, 16/16 in 3.01s; `npx tsc --noEmit` → clean; `pnpm build` → "Compiled successfully in 6.5s", 7 static routes.
  - `git diff --stat main HEAD -- pipeline/ tests/` is empty; design-pass only touched `web/src/**` (11 files, +593/-199) — the atlas-artifact gap is a pre-existing pipeline/provenance issue, not a design-pass regression.
  - `.github/workflows/ci.yml` wires `release-readiness` then `browser-smoke` with Playwright on PRs to `main`; `docs/TRACEABILITY.md` shows `release_blocking_ids_present: true` (no traceability gaps).

## Gate C (follow-ups cleared 2026-04-23)

- Gate: `Gate C`
- Date: `2026-04-23`
- Reviewer: `Claude`
- Outcome: `pass`
- Blocking issues: none
- Approved follow-ups: none carried forward
- Evidence:
  - `web/src/app/about/page.tsx:62-69` rewritten — Steps 2 and 3 now read "Observe from Satellites" and "Correlate Evidence with Conditions"; NIR reframed as one supporting evidence layer instead of the headline method, matching `methodology.md §Evidence Layers` and SpotPanel's "Exploratory detection telemetry".
  - `web/src/components/MapView.tsx:39-44` (`getEvidenceBadge`) rewritten to consume `evidence_confidence_label` and render "High evidence / Moderate evidence / Low evidence / No evidence" — identical vocabulary to `formatEvidenceLabel` at `web/src/lib/spotData.ts:228`. Map popup and SpotPanel now speak the same words for the same field.
  - `web/src/components/AtlasMap.tsx` deleted — dead code with divergent legend thresholds removed; `/atlas` continues to redirect to `/?analysis=atlas`.
  - tests green: `npx vitest run` → 5 files, 16/16 passing; `npx tsc --noEmit` → clean.

## Gate D (resolution 2026-04-23)

- Gate: `Gate D`
- Date: `2026-04-23`
- Reviewer: `Claude`
- Outcome: `pass`
- Blocking issues: none
- Approved follow-ups:
  - continue treating `web/public/data/atlas/sections.json` as a tracked generated artifact (the upstream `ns_atlas_sections.geojson` remains gitignored); regenerate and recommit when the pipeline is rerun end-to-end.
- Evidence:
  - `web/public/data/atlas/sections.json` committed (removed from `.gitignore` alongside the same pattern already used for `segments-*.json` and `atlas/gallery.json`).
  - `pipeline/data/manifests/release_readiness_report.json` regenerated 2026-04-23T22:52:16Z — `ready: true`, all artifact/provenance/policy/docs checks pass, `failures: []`.
  - `web/public/data/dataset-manifest.json` restored to advertise the full artifact set including `atlas_sections`.
  - CI on `main` was red for the atlas gap since at least 2026-04-18 (GitHub run 24606028132); this commit is the first state from which `release-readiness` should pass cleanly.
