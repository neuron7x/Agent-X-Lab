# Deploy AXL-UI to Vercel

## Prerequisites

- Vercel account (free)
- GitHub repo connected to Vercel
- BFF Worker deployed (see `docs/deploy/cloudflare-worker.md`)

## Steps

### 1. Import project

1. Go to [vercel.com/new](https://vercel.com/new)
2. Select your GitHub repo
3. Framework: **Vite** (auto-detected)
4. Root directory: `.` (repo root, where `package.json` is)

### 2. Set environment variables

In Vercel project **Settings → Environment Variables**:

| Name | Value | Environment |
|------|-------|-------------|
| `VITE_AXL_API_BASE` | `https://axl-bff.<your-subdomain>.workers.dev` | Production |
| `VITE_AXL_API_BASE` | `https://axl-bff.<your-subdomain>.workers.dev` | Preview |
| `VITE_AXL_API_BASE` | `http://localhost:8787` | Development |

> ⚠️ Never set `GITHUB_TOKEN` or any secret as a `VITE_` variable — they would be bundled into the JS build and exposed to users.

### 3. Deploy

```bash
# Via Vercel CLI (optional — Vercel auto-deploys on push)
npm i -g vercel
vercel --prod
```

Or just push to `main` — Vercel auto-deploys.

### 4. Verify

```bash
# Should return your SPA, not 404
curl -I https://your-project.vercel.app/

# Deep link should also work (rewrites catch all routes)
curl -I https://your-project.vercel.app/settings
```

### 5. Update BFF ALLOWED_ORIGINS

After deploy, update the Worker secret:

```bash
cd workers/axl-bff
wrangler secret put ALLOWED_ORIGINS
# Enter: https://your-project.vercel.app,https://your-project-git-main.vercel.app
```

## Local dev

```bash
cp .env.example .env.local
# Edit .env.local: set VITE_AXL_API_BASE=http://localhost:8787

# Terminal 1: run Worker locally
cd workers/axl-bff && npm run dev

# Terminal 2: run UI
npm run dev
```

## Build command reference

| Command | Description |
|---------|-------------|
| `npm run build` | Production build (used by Vercel) |
| `npm run build:dev` | Dev build with source maps |
| `npm run test` | Vitest unit tests |
| `npm run lint` | ESLint |
