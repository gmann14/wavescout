# Deploying WaveScout

## Quick Start (15 minutes)

### 1. Vercel Setup

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click "Add New Project"
3. Import `gmann14/wavescout`
4. Configure:
   - **Root Directory**: `web`
   - **Framework**: Next.js (auto-detected)
   - **Build Command**: `pnpm build` (auto-detected from vercel.json)
5. Add environment variable:
   - `NEXT_PUBLIC_MAPBOX_TOKEN` = your Mapbox token (from `web/.env.local`)
6. Click Deploy

Site will be live at `wavescout.vercel.app` within ~2 minutes.

### 2. GitHub Actions CI

The CI workflow at `.github/workflows/ci.yml` runs type checking and build on every push to `main` that touches `web/`.

Add the Mapbox token to GitHub Secrets:
1. Go to repo Settings > Secrets and variables > Actions
2. Add secret: `MAPBOX_TOKEN` = your Mapbox token

### 3. Mapbox Token Security

In your [Mapbox dashboard](https://account.mapbox.com/):
1. Go to Access tokens
2. Edit your token's URL restrictions
3. Add allowed URLs:
   - `https://wavescout.vercel.app`
   - `http://localhost:3000`
   - (add custom domain later if you register one)

## What's Configured

| File | Purpose |
|------|---------|
| `web/vercel.json` | Vercel project config (framework, build commands) |
| `.github/workflows/ci.yml` | CI: type check + build on push/PR |
| `web/next.config.ts` | Image optimization, cache headers for gallery/atlas images |
| `web/public/robots.txt` | Search engine crawling rules |
| `web/src/app/layout.tsx` | OpenGraph + Twitter meta tags for link sharing |

## Auto-Deploy

With Vercel's GitHub integration, every push to `main` auto-deploys. PRs get preview URLs.

## Custom Domain (Optional)

1. Register `wavescout.ca` (or similar) at any registrar
2. In Vercel dashboard: Settings > Domains > Add domain
3. Add the DNS records Vercel provides at your registrar
4. Update `NEXT_PUBLIC_SITE_URL` env var in Vercel to your custom domain
5. Update Mapbox token URL restrictions to include the new domain

## Image CDN (Later, when needed)

Gallery images (~300MB) are served from `web/public/data/gallery/`. This works fine on Vercel free tier at low traffic. When atlas images grow past 1GB or traffic increases, move to Cloudflare R2. See `.claude/SPEC-deployment.md` for details.
