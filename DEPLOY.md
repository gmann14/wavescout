# Deploying WaveScout

*Updated: 2026-05-25*

This document describes how to deploy the current static web viewer. It does not assume a production deployment already exists.

## Image Delivery Decision

The current default is **static-public hosting**: image files live in
`web/public/gallery/` and `web/public/atlas-gallery/` and are shipped
as part of the deploy artifact. Keep this mode until atlas coverage or
traffic makes the deploy artifact uncomfortably large (rule of thumb:
when `web/public/gallery/` plus `web/public/atlas-gallery/` exceeds
roughly 500MB, or the build artifact starts pushing platform limits).

When that threshold is hit, switch to **CDN delivery** by setting
`WAVESCOUT_GALLERY_URL_PREFIX` to an absolute `https://` origin
(optionally including a shared base path) before running the build
scripts. If the prefix ends with `/gallery` or `/atlas-gallery`, the
builders treat those as sibling collection directories under the same
parent so both spot-gallery and atlas-gallery URLs remain valid. The
pipeline will:

- still write local copies into `web/public/gallery/` and
  `web/public/atlas-gallery/` (so a fall-back static deploy stays
  possible),
- rewrite emitted image paths in `gallery.json` and `atlas/gallery.json`
  to absolute https URLs under the prefix,
- record `image_delivery = {"mode": "cdn", "gallery_url_prefix": "..."}`
  in `dataset-manifest.json`.

The validators (`validate_public_dataset.py`, `pnpm validate:assets`)
read `image_delivery` from the manifest and:

- treat web-root-relative paths as local files that must exist under
  `web/public/`,
- allow `https://` paths only when the manifest's
  `image_delivery.mode` is `cdn`,
- always reject `http://`, protocol-relative `//`, and other schemes.

Object storage upload (for example to Cloudflare R2) is out of scope
for the pipeline; configure that as a deploy step that mirrors
`web/public/gallery/` and `web/public/atlas-gallery/` to the CDN
origin.

## Preconditions

Before deploying, confirm:

- the promoted dataset has been generated, validated, and promoted
- the promoted dataset satisfies [docs/DATA-CONTRACTS.md](docs/DATA-CONTRACTS.md)
- the public payload satisfies [docs/PUBLIC-OUTPUT-POLICY.md](docs/PUBLIC-OUTPUT-POLICY.md)
- `web/public/data/` contains the intended static payloads
- `web/public/gallery/` contains every non-null image referenced by `web/public/data/gallery.json`
- `web/public/atlas-gallery/` contains every non-null image referenced by `web/public/data/atlas/gallery.json`, if atlas gallery scenes are present
- `NEXT_PUBLIC_MAPBOX_TOKEN` is available for the target environment
- the web app builds locally with `pnpm build`
- `pnpm build` runs `pnpm validate:assets` first and must fail if gallery manifests reference missing public images
- `python3.12 pipeline/scripts/check_release_readiness.py` has passed
- `python3.12 pipeline/scripts/promote_public_dataset.py` has been run with a recorded `Gate D` review

## Local Validation

```bash
python3.12 pipeline/scripts/check_release_readiness.py --include-e2e
```

Verify:

- the map route loads
- the atlas route loads
- the compare route loads
- visible gallery images render with nonzero dimensions
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
- visible gallery images render with nonzero dimensions
- route navigation works for `Map`, `Atlas`, `Compare`, `How It Works`, and `About`
- there are no obvious console or hydration errors

## Notes

- `web/vercel.json` contains the Vercel build settings checked into the repo.
- Deployment should be considered incomplete until [docs/RELEASE-CHECKLIST.md](docs/RELEASE-CHECKLIST.md) is complete.
