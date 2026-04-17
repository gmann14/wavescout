# WaveScout Web App

This is the static Next.js viewer for WaveScout.

## What It Contains

- `Map` for confirmed spots and candidate segments
- `Atlas` for systematic coastline browsing
- `Compare` for same-date cross-spot inspection
- markdown-driven `How It Works`
- static `About`

The app reads generated files from `web/public/data/`. It does not query Google Earth Engine directly.

## Local Development

```bash
pnpm install
cp .env.local.example .env.local
pnpm dev
```

Required environment variable:

- `NEXT_PUBLIC_MAPBOX_TOKEN`

## Production Build

```bash
pnpm build
pnpm start
```

## Data Dependency

Refresh the static payloads from the pipeline with:

```bash
python3 ../pipeline/scripts/build_web_data.py
python3 ../pipeline/scripts/build_atlas_web_data.py
```

## Testing Direction

The frontend test plan is defined in [docs/ROADMAP.md](../docs/ROADMAP.md). The key missing coverage areas are:

- component states
- navigation smoke tests
- map/detail UX regression checks
- compare-page date integrity

The normative frontend behavior docs are:

- [docs/UI-STATES.md](../docs/UI-STATES.md)
- [docs/DATA-CONTRACTS.md](../docs/DATA-CONTRACTS.md)
- [docs/PUBLIC-OUTPUT-POLICY.md](../docs/PUBLIC-OUTPUT-POLICY.md)

Initial frontend test commands:

```bash
pnpm test
pnpm test:e2e
```
