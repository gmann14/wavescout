# Codex Cloud Setup

*Updated: 2026-04-19*

This document describes the recommended Codex cloud environment for this repo.

## Recommended Environment

Use these settings when creating the environment:

- Repository: `gmann14/wavescout`
- Container image: `universal`
- Container caching: `On`
- Setup script: `Manual`
- Agent internet access: `On`

Why:

- the repo uses both Python and `pnpm`
- several pipeline scripts call network services
- Playwright, Python wheels, and map/web dependencies are easier to manage in `universal`
- container caching saves a lot of repeated setup time

## What Works In Cloud

Should work well:

- `pytest`
- `cd web && pnpm test`
- `cd web && pnpm exec tsc --noEmit`
- `cd web && pnpm build`
- `python pipeline/scripts/11_score_geometry.py`
- `python pipeline/scripts/20_rank_segments.py --validate`
- `python pipeline/scripts/build_web_data.py`
- `python pipeline/scripts/build_atlas_web_data.py`

Will not work without credentials or extra setup:

- Google Earth Engine scripts
- map rendering without a Mapbox token
- any API-dependent pipeline step if internet access is disabled
- bathymetry scoring if the GEBCO NetCDF is not present in the environment

## Required Environment Variables

Add these in the Codex environment UI:

- `GEE_PROJECT`
- `NEXT_PUBLIC_MAPBOX_TOKEN`

## Required Secrets

If you want Google Earth Engine scripts to work in cloud, add a secret containing the service-account JSON. Example secret name:

- `GEE_SERVICE_ACCOUNT_JSON`

Do not rely on interactive `earthengine authenticate` in cloud.

## Recommended Setup Script

Use a manual setup script like this:

```bash
set -euxo pipefail

python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cd web
corepack enable || true
pnpm install --frozen-lockfile
pnpm exec playwright install --with-deps
```

## Optional Earth Engine Auth Bootstrap

If the environment supports exposing secrets into the shell, write the service-account JSON to a file and point Google auth at it:

```bash
mkdir -p /workspace/.secrets
printf '%s' "$GEE_SERVICE_ACCOUNT_JSON" > /workspace/.secrets/gee-service-account.json
export GOOGLE_APPLICATION_CREDENTIALS=/workspace/.secrets/gee-service-account.json
```

If secret expansion is not available in the setup script, add the same commands to the first shell session before running GEE-backed scripts.

## First Validation Commands

After setup, validate in this order:

```bash
. venv/bin/activate
python pipeline/scripts/11_score_geometry.py
python pipeline/scripts/20_rank_segments.py --validate
python pipeline/scripts/build_web_data.py
python pipeline/scripts/validate_public_dataset.py
pytest

cd web
pnpm test
pnpm exec tsc --noEmit
pnpm build
```

## Minimal Cloud Mode

If you only want Codex cloud for coding, tests, and the static web app, you can skip Earth Engine auth and still use the environment for:

- ranking and public-data rebuilds from checked-in/generated artifacts
- frontend work
- docs and spec work
- pipeline tests that do not require fresh GEE exports

## Known Limitations

- some pipeline stages still depend on external APIs such as Overpass, CHS, Open-Meteo, or Earth Engine
- `11_score_geometry.py` can run offline now by reusing cached road scores, but fresh road downloads still need internet
- the web viewer needs `NEXT_PUBLIC_MAPBOX_TOKEN` even though it only reads static data
