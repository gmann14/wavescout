# WaveScout

WaveScout is a Nova Scotia surf-discovery project built from precomputed satellite evidence, coastline geometry, and ocean context. The repo contains two main surfaces:

- a Python pipeline that produces ranked coastline artifacts and image galleries
- a static Next.js viewer that explores those artifacts on a map, in an atlas, and in same-date comparisons

## Current Status

As of 2026-04-18:

- feasibility work is complete enough to justify continuing with imagery-assisted discovery
- the repo contains pipeline scripts through ranking and web-data export
- the web app exists locally and renders precomputed Nova Scotia data
- the remaining work is product hardening: contamination handling, clearer score semantics, UX polish, and automated tests

The canonical planning docs are:

- [docs/SPEC.md](docs/SPEC.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/IMPLEMENTATION-BACKLOG.md](docs/IMPLEMENTATION-BACKLOG.md)
- [docs/IMPLEMENTATION-KICKOFF.md](docs/IMPLEMENTATION-KICKOFF.md)
- [docs/MIGRATION-STRATEGY.md](docs/MIGRATION-STRATEGY.md)
- [docs/DATA-CONTRACTS.md](docs/DATA-CONTRACTS.md)
- [docs/UI-STATES.md](docs/UI-STATES.md)
- [docs/PUBLIC-OUTPUT-POLICY.md](docs/PUBLIC-OUTPUT-POLICY.md)
- [docs/REVIEW-GATES.md](docs/REVIEW-GATES.md)
- [docs/RELEASE-CHECKLIST.md](docs/RELEASE-CHECKLIST.md)
- [docs/TRACEABILITY.md](docs/TRACEABILITY.md)
- [docs/METHODOLOGY.md](docs/METHODOLOGY.md)
- [FEASIBILITY-STATUS.md](FEASIBILITY-STATUS.md)

## Product Definition

The MVP is a static Nova Scotia explorer, not a live forecasting product.

Users should be able to:

- inspect confirmed spots and candidate coastline segments on a map
- understand why a location is ranked the way it is
- review satellite evidence and caveats
- compare locations on the same acquisition date
- browse the coastline atlas without triggering new processing jobs

The MVP should not claim that a spot is good, safe, accessible, or working today.

## Repo Structure

```text
pipeline/
  configs/          region, spot, and atlas config JSON
  scripts/          numbered pipeline stages plus web-data builders
  data/             generated manifests, coastline artifacts, galleries, atlas outputs
docs/
  SPEC.md           product and UX source of truth
  ROADMAP.md        ordered implementation plan with red/green TDD stages
  METHODOLOGY.md    user-facing explanation of how the evidence works
web/
  src/app/          Next.js routes
  src/components/   viewer components
  public/data/      generated static payloads consumed by the web app
```

## Setup

### Pipeline

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
earthengine authenticate
```

Set `GEE_PROJECT` in `.env`.

### Web

```bash
cd web
pnpm install
cp .env.local.example .env.local
pnpm dev
```

Set `NEXT_PUBLIC_MAPBOX_TOKEN` in `web/.env.local`.

### Rebuild Web Data

```bash
python3 pipeline/scripts/build_web_data.py
python3 pipeline/scripts/build_atlas_web_data.py
```

## Testing Status

There is not yet a complete automated test harness for the pipeline and web app. The required red/green test plan is defined in [docs/ROADMAP.md](docs/ROADMAP.md) and should be treated as delivery work, not optional cleanup.

Initial test commands:

```bash
pytest
cd web && pnpm test
cd web && pnpm test:e2e
```

## Notes

- `web/public/data/methodology.md` is the web-served copy of [docs/METHODOLOGY.md](docs/METHODOLOGY.md) and should stay in sync.
- Generated pipeline data can be large; prefer rebuilding derived web assets rather than duplicating them.
- Treat any precise counts in generated artifacts as snapshots, not product promises.
