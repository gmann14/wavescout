# Deploying WaveScout

*Updated: 2026-04-17*

This document describes how to deploy the current static web viewer. It does not assume a production deployment already exists.

## Preconditions

Before deploying, confirm:

- the promoted dataset has been generated, validated, and promoted
- the promoted dataset satisfies [docs/DATA-CONTRACTS.md](docs/DATA-CONTRACTS.md)
- the public payload satisfies [docs/PUBLIC-OUTPUT-POLICY.md](docs/PUBLIC-OUTPUT-POLICY.md)
- `web/public/data/` contains the intended static payloads
- `NEXT_PUBLIC_MAPBOX_TOKEN` is available for the target environment
- the web app builds locally with `pnpm build`
- `python3 pipeline/scripts/check_release_readiness.py` has passed
- `python3 pipeline/scripts/promote_public_dataset.py` has been run with a recorded `Gate D` review

## Local Validation

```bash
python3 pipeline/scripts/check_release_readiness.py --include-e2e
```

Verify:

- the map route loads
- the atlas route loads
- the compare route loads
- the methodology page renders markdown correctly
- the release-readiness report exists in `pipeline/data/manifests/release_readiness_report.json`
- the promoted dataset record exists in `pipeline/data/manifests/promoted_dataset_record.json`

## Vercel Deployment

If deploying with Vercel:

1. Create or select a Vercel project.
2. Set the root directory to `web`.
3. Ensure install and build commands are:
   - `pnpm install --frozen-lockfile`
   - `pnpm build`
4. Add `NEXT_PUBLIC_MAPBOX_TOKEN`.
5. Trigger a deployment.

## Post-Deploy Checks

After deployment, verify:

- the deployed build uses the intended static dataset
- map tiles render
- gallery image paths resolve
- route navigation works for `Map`, `Atlas`, `Compare`, `How It Works`, and `About`
- there are no obvious console or hydration errors

## Notes

- `web/vercel.json` contains the Vercel build settings checked into the repo.
- Deployment should be considered incomplete until [docs/RELEASE-CHECKLIST.md](docs/RELEASE-CHECKLIST.md) is complete.
