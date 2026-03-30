# Spec: Deployment Strategy

> Get WaveScout live on the internet — static site hosting, image CDN, CI/CD, and domain.

## Problem

WaveScout is currently local-only. The Next.js app runs at `localhost:3000` and all data (JSON + gallery/atlas images) is served from `web/public/`. To share it with other surfers or get feedback, it needs to be deployed.

Key constraints:
- **Static site**: Next.js with static export (no server-side rendering needed — all data is precomputed)
- **Large image assets**: ~300MB+ of gallery PNGs (31 spots x ~14 images x 2 bands x ~200KB), plus atlas images (2,839 sections) which could reach 2-5GB at full coverage
- **Low traffic initially**: Graham + a few friends, maybe 10-50 users/month
- **Budget**: Minimal — free tier or near-free preferred
- **Mapbox dependency**: Requires a client-side token for map tiles

## Hosting Options

### Recommended: Vercel (free tier)

| Aspect | Details |
|--------|---------|
| Cost | Free for hobby projects |
| Build | Auto-detects Next.js, runs `pnpm build` |
| Deploy | Git push to main triggers deploy |
| CDN | Global edge network included |
| Limits | 100GB bandwidth/month (free tier), 1000 deploys/month |
| Domain | `wavescout.vercel.app` free, custom domain supported |

**Pros**: Zero-config for Next.js, fast deploys, preview URLs for PRs.
**Cons**: 100GB bandwidth could be tight if atlas images are served from Vercel. Image-heavy site needs separate CDN.

### Alternative: Cloudflare Pages

| Aspect | Details |
|--------|---------|
| Cost | Free tier (unlimited bandwidth) |
| Build | Supports Next.js static export |
| Limits | 500 deploys/month, 25MB per file |
| Domain | `wavescout.pages.dev` free |

**Pros**: Unlimited bandwidth on free tier, Cloudflare CDN built in.
**Cons**: Slightly more setup for Next.js, 25MB file limit (fine for our images).

### Not recommended for this project

- **Railway**: Better for backend services, overkill for static site
- **AWS Amplify**: More complex setup, AWS billing model is harder to predict
- **GitHub Pages**: No Next.js build support without custom workflow, limited

## Image CDN Strategy

Gallery and atlas images should NOT be served from the site host. They are too large and would eat through bandwidth limits quickly.

### Recommended: Cloudflare R2

| Aspect | Details |
|--------|---------|
| Storage cost | $0.015/GB/month (300MB = $0.005/month) |
| Egress | Free (no bandwidth charges) |
| Setup | S3-compatible API, public bucket with custom domain |
| Limits | 10GB free storage, 10M free reads/month |

**Workflow**:
1. Gallery/atlas images uploaded to R2 bucket during CI/CD or manual deploy
2. R2 bucket gets a custom subdomain: `images.wavescout.ca` or `cdn.wavescout.ca`
3. Web app references images via CDN URL instead of relative paths
4. Cache headers set for long TTL (images rarely change)

**Implementation change**: Update `build_web_data.py` to output image URLs with a configurable CDN prefix:

```python
CDN_PREFIX = os.environ.get("CDN_URL", "/data/gallery")
# In gallery manifest:
# "url": f"{CDN_PREFIX}/lawrencetown-beach/lawrencetown-beach_2024-08-30_0.3m_rgb.png"
```

Web components read the URL directly — no code change needed beyond the manifest.

### Alternative: AWS S3 + CloudFront

More infrastructure to manage, but well-documented. ~$0.023/GB storage + $0.085/GB egress. Less favorable than R2 for this use case due to egress costs.

### Alternative: Just serve from Vercel/Cloudflare Pages

For the initial launch with ~300MB of gallery images and low traffic, serving images directly from the static host is fine. Defer CDN separation until atlas images push past 1GB or traffic exceeds free tier limits.

**Recommendation**: Start by serving images from the static host. Split to R2 when atlas coverage grows past 1GB.

## Mapbox Token Management

The map requires `NEXT_PUBLIC_MAPBOX_TOKEN` at build time (it is embedded in the client bundle).

### Strategy

1. Create a Mapbox account with a free tier token (50,000 map loads/month free)
2. Set the token as an environment variable in the hosting platform (Vercel/Cloudflare)
3. Restrict the token by URL referrer in Mapbox dashboard: `wavescout.vercel.app`, `wavescout.ca`, `localhost:3000`
4. Do NOT commit the token to the repo (already gitignored in `web/.env.local`)

### Token rotation

If the token is ever exposed:
1. Rotate in Mapbox dashboard
2. Update in hosting platform env vars
3. Redeploy

## Domain Options

| Option | Cost | Notes |
|--------|------|-------|
| `wavescout.vercel.app` | Free | Default Vercel subdomain |
| `wavescout.ca` | ~$15/year | .ca domain, Canadian project |
| `wavescout.surf` | ~$35/year | .surf TLD exists, niche but memorable |
| `wavescout.io` | ~$30/year | Tech-standard TLD |

**Recommendation**: Start with `wavescout.vercel.app`, register `wavescout.ca` when ready to share publicly. Point DNS to Vercel (or Cloudflare if using Pages).

## CI/CD Pipeline

### GitHub Actions workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
    paths:
      - 'web/**'
      - 'pipeline/scripts/build_web_data.py'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
          cache-dependency-path: web/pnpm-lock.yaml

      - name: Install dependencies
        working-directory: web
        run: pnpm install --frozen-lockfile

      - name: Type check
        working-directory: web
        run: npx tsc --noEmit

      - name: Build
        working-directory: web
        run: pnpm build
        env:
          NEXT_PUBLIC_MAPBOX_TOKEN: ${{ secrets.MAPBOX_TOKEN }}

      # If using Vercel, this step is handled by Vercel's GitHub integration
      # If using Cloudflare Pages, use wrangler:
      # - name: Deploy to Cloudflare Pages
      #   uses: cloudflare/wrangler-action@v3
      #   with:
      #     command: pages deploy web/out --project-name=wavescout
```

### If using Vercel's GitHub integration (simpler)

No GitHub Actions needed — Vercel auto-deploys on push to main. Just configure:
1. Link GitHub repo in Vercel dashboard
2. Set root directory to `web/`
3. Set build command: `pnpm build`
4. Set environment variables: `NEXT_PUBLIC_MAPBOX_TOKEN`

### Image upload step (when using R2)

Add a separate workflow or post-build step:

```yaml
- name: Sync gallery images to R2
  run: |
    aws s3 sync web/public/data/gallery/ s3://wavescout-images/gallery/ \
      --endpoint-url ${{ secrets.R2_ENDPOINT }} \
      --cache-control "public, max-age=31536000"
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.R2_ACCESS_KEY }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.R2_SECRET_KEY }}
```

## Cost Estimates

### At current scale (~300MB images, <50 users/month)

| Service | Monthly Cost |
|---------|-------------|
| Vercel (free tier) | $0 |
| Mapbox (free tier, <50k loads) | $0 |
| Domain (wavescout.ca) | ~$1.25 ($15/year) |
| Cloudflare R2 (if needed) | $0 (within free tier) |
| **Total** | **~$1.25/month** |

### At medium scale (~2GB images, 500 users/month)

| Service | Monthly Cost |
|---------|-------------|
| Vercel (free tier, maybe Pro at $20) | $0-20 |
| Mapbox (free tier still covers it) | $0 |
| Cloudflare R2 (2GB storage) | $0.03 |
| Domain | ~$1.25 |
| **Total** | **~$1.25-21/month** |

### At larger scale (~10GB images, 5000 users/month)

| Service | Monthly Cost |
|---------|-------------|
| Vercel Pro | $20 |
| Mapbox (may approach 50k limit) | $0-50 |
| Cloudflare R2 (10GB) | $0.15 |
| Domain | ~$1.25 |
| **Total** | **~$21-71/month** |

## Implementation Steps

### Phase 1: Basic deployment (1-2h)

1. Ensure `pnpm build` produces a clean static export (verify `next.config.js` has `output: 'export'` or equivalent)
2. Connect GitHub repo to Vercel
3. Set `NEXT_PUBLIC_MAPBOX_TOKEN` in Vercel env vars
4. Deploy — verify at `wavescout.vercel.app`
5. Test: map loads, gallery images display, atlas page works

### Phase 2: Domain + polish (1h)

1. Register `wavescout.ca`
2. Point DNS to Vercel
3. Restrict Mapbox token to production domain + localhost
4. Add `robots.txt` and basic meta tags

### Phase 3: Image CDN (2-3h, when needed)

1. Create Cloudflare R2 bucket
2. Upload gallery images
3. Configure public access with custom subdomain
4. Update `build_web_data.py` to use CDN prefix
5. Update web components if needed
6. Add R2 sync to CI/CD

## Next.js Static Export Notes

The current app may use features that require a server (API routes, server components with dynamic data). Verify:

- [ ] `next.config.js` includes `output: 'export'` (or `next export` works)
- [ ] No `getServerSideProps` usage (only `getStaticProps` or client-side fetching)
- [ ] All data loaded from `public/data/` via fetch (client-side) — no Node.js file reads
- [ ] Mapbox GL works in static export (it is client-side only, should be fine)

If static export is not feasible, Vercel still supports full Next.js with server-side rendering at no extra cost on free tier.

## Effort Estimate

| Task | Time |
|------|------|
| Phase 1: Basic deploy | 1-2h |
| Phase 2: Domain setup | 1h |
| Phase 3: Image CDN | 2-3h |
| **Total** | **4-6h** |

## Dependencies

- GitHub repo (`gmann14/wavescout`) — already exists
- Mapbox account with API token — already have one for local dev
- Vercel account (free, GitHub login)
- Domain registrar account (for .ca domain)

## Open Questions

1. **Static export vs. full Next.js?** Static export is simpler and cheaper, but loses the ability to add API routes later (e.g., for saving atlas labels). Could use Vercel serverless functions if needed.
2. **Should gallery images be committed to git?** Currently they are in `web/public/data/gallery/` and untracked. Options: (a) commit them (bloats repo), (b) generate during CI/CD (slow, requires GEE auth), (c) upload to R2 separately (cleanest).
3. **Atlas images**: At 2,839 sections x ~12 images x 2 bands x 200KB = ~13GB. This definitely needs a CDN, not static hosting. May want to generate atlas images on-demand or limit initial deployment to the gallery images only.
4. **Preview deployments**: Vercel creates preview URLs for every PR. Should gallery images be included in preview builds, or only in production?
