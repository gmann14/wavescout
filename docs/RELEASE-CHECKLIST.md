# WaveScout Release Checklist

*Updated: 2026-05-05*  
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
- any non-null gallery image path points to a missing file under `web/public/`

## Artifact Checks

- `web/public/data/dataset-manifest.json` exists
- `web/public/data/spots.json` exists
- `web/public/data/segments-high.json` exists
- `web/public/data/segments-all.json` exists
- `web/public/data/gallery.json` exists
- `web/public/data/atlas/sections.json` exists
- `web/public/data/atlas/gallery.json` exists
- `web/public/data/spots/<slug>.json` exists for all public named spots
- `web/public/gallery/` contains every non-null image referenced by `web/public/data/gallery.json`
- `web/public/atlas-gallery/` contains every non-null image referenced by `web/public/data/atlas/gallery.json`, if atlas gallery scenes are present

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
- gallery image paths are web-root-relative and resolve under `web/public/`

## Policy Checks

- all `internal_only` entities are absent from public payloads
- all `public_coarse` entities respect coarse precision rules
- no candidate is rendered as a named public spot
- report/takedown path exists in the product or linked documentation

## Build And Validation Commands

Run and record results for:

```bash
python3 pipeline/scripts/check_release_readiness.py
```

The web build also runs gallery asset validation before compiling:

```bash
cd web && pnpm build
```

Include browser verification before external release claims:

```bash
python3 pipeline/scripts/check_release_readiness.py --include-e2e
```

Promotion must use the explicit promotion command after a green readiness report and a recorded `Gate D` review:

```bash
python3 pipeline/scripts/promote_public_dataset.py \
  --release-reviewer "<name>" \
  --policy-reviewer "<name>" \
  --review-record "docs/RELEASE-RECORD-TEMPLATE.md or linked issue/PR record" \
  --gate-outcome pass
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
- [RELEASE-RECORD-TEMPLATE.md](RELEASE-RECORD-TEMPLATE.md) or an equivalent durable record is ready for `Gate D`

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

The current durable review log may live in [REVIEW-RECORDS.md](REVIEW-RECORDS.md) or an equivalent PR/release record.
