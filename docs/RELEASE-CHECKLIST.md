# WaveScout Release Checklist

*Updated: 2026-04-18*  
*Status: Required pre-release and promotion gate*

## Purpose

This checklist must be completed before promoting a dataset or calling the web build release-ready.

This checklist is the execution artifact for `Gate D` in [REVIEW-GATES.md](REVIEW-GATES.md).

## Stop Conditions

Do not release if any are true:

- the promoted dataset is missing a required artifact from [DATA-CONTRACTS.md](DATA-CONTRACTS.md)
- payloads still rely on ambiguous legacy `confidence`
- public output violates [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md)
- required UI states in [UI-STATES.md](UI-STATES.md) are not implemented
- traceability gaps remain for blocking spec requirements

## Artifact Checks

- `web/public/data/dataset-manifest.json` exists
- `web/public/data/spots.json` exists
- `web/public/data/segments-high.json` exists
- `web/public/data/segments-all.json` exists
- `web/public/data/gallery.json` exists
- `web/public/data/atlas/sections.json` exists
- `web/public/data/atlas/gallery.json` exists
- `web/public/data/spots/<slug>.json` exists for all public named spots

## Provenance Checks

- all top-level public manifests include `run_id`
- all top-level public manifests include `generated_at_utc`
- all top-level public manifests include `code_version`
- dataset manifest includes `config_version`

## Contract Checks

- no public payload requires legacy `confidence`
- selectable entities include `explanation`
- score fields are normalized to `surf_potential_score`
- confidence fields are normalized to `evidence_confidence_level` and label
- publication status is present for public entities

## Policy Checks

- all `internal_only` entities are absent from public payloads
- all `public_coarse` entities respect coarse precision rules
- no candidate is rendered as a named public spot
- report/takedown path exists in the product or linked documentation

## Build And Validation Commands

Run and record results for:

```bash
python3 pipeline/scripts/build_web_data.py
python3 pipeline/scripts/build_atlas_web_data.py
cd web && pnpm install
cd web && pnpm build
```

When tests exist, also run:

```bash
pytest
cd web && pnpm test
cd web && pnpm test:e2e
```

## Manual QA

### Map

- map loads with valid token
- legend explains confirmed, candidate, and context layers
- low-confidence selection shows caution language
- missing detail data fails gracefully

### Detail Panel

- confirmed and candidate labels are distinct
- no-gallery state is explicit
- no-profile state is explicit
- provenance is visible or reachable

### Atlas

- atlas section selection works
- atlas explains section browsing semantics
- empty-gallery section state is explicit

### Compare

- rows contain same-date scenes only
- sparse-date warning appears when forced by query param
- no-match date state is explicit

### Content Pages

- methodology renders
- about page includes uncertainty and scope boundaries

## Documentation Sync

- [README.md](../README.md) matches current scope
- [SPEC.md](SPEC.md) matches current release rules
- [DATA-CONTRACTS.md](DATA-CONTRACTS.md) matches actual payloads
- [UI-STATES.md](UI-STATES.md) matches actual UI behavior
- [REVIEW-GATES.md](REVIEW-GATES.md) matches the actual signoff flow used during implementation
- [DEPLOY.md](../DEPLOY.md) matches actual deployment process

## Sign-Off

Record before promotion:

- dataset id
- run id
- code version
- release reviewer
- policy reviewer
- date
- `Gate D` outcome
- location of the review record
