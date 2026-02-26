─── BFF ARCHITECTURE (v2 — production) ───────────────────────────────────────

SECURITY CONTRACT: UI contains zero GitHub tokens. All auth is server-side.

Data flow:
  Browser → VITE_AXL_API_BASE (Cloudflare Worker)
           → GitHub API (server-side GITHUB_TOKEN, never exposed to browser)
           → KV cache (TTL 60s, webhook invalidation)

Endpoints used by UI:
  GET  /healthz              → BFF reachability probe (isConfigured check)
  GET  /vr                   → VR.json (cached)
  POST /dispatch/run-engine  → trigger engine via repository_dispatch
  GET  /gh/*                 → allowlist proxy (only /repos/{owner}/{repo}/*)
  POST /webhook/github       → HMAC-verified invalidation (server receives only)

Environment variables:
  VITE_AXL_API_BASE   — Worker URL (required; set in Vercel project settings)
  (all secrets live in Cloudflare Worker secrets, never in Vercel/browser)

─────────────────────────────────────────────────────────────────────────────

Build Agent-X-Lab Control Interface — AXL-UI v1.0. Production-grade cognitive operations environment. Desktop only, min-width 1280px. No templates. No generic patterns. No clarifying questions — make all decisions from this spec.

─── BUILD ORDER ───────────────────────────────────────────────────────────────

Step 1: Design system + base components

Step 2: Full layout with mock data matching exact VR.json schema

Step 3: BFF API hooks replacing mock data (all calls via VITE_AXL_API_BASE Worker — zero direct api.github.com)

Step 4: Error/empty states

Complete all 4 steps in one build. No checkpoints.

─── DESIGN SYSTEM ─────────────────────────────────────────────────────────────

Typography: JetBrains Mono exclusively — load from Google Fonts. Every label, value, heading, button. Zero sans-serif anywhere.

Colors (CSS variables):

--bg-void: #050508

--bg-surface: #0c0c12

--bg-elevated: #12121a

--border-dim: #1a1a28

--border-active: #2a2a40

--signal-pass: #00e87a

--signal-fail: #ff2d55

--signal-warn: #ffaa00

--signal-running: #4488ff

--signal-assumed: #aa66ff

--text-primary: #e8e8f0

--text-secondary: #666688

--text-dim: #333348

Animations:

- PASS state: 400ms glow pulse on --signal-pass

- FAIL state: hard cut, zero animation, immediate red

- RUNNING: 2s breathing border animation

- Page load: staggered panel reveal, 80ms offset per panel

- New data: scan-line from top, 150ms

- Connection dot: 2s slow pulse

─── MOCK DATA (matches real VR.json schema exactly) ────────────────────────────

{

  "status": "RUN",

  "utc": "2026-02-22T18:16:13Z",

  "work_id": "e0371af18cddd70f",

  "blockers": [],

  "metrics": {

    "pass_rate": 1.0,

    "baseline_pass": true,

    "catalog_ok": true,

    "determinism": "ASSUMED_SINGLE_RUN",

    "evidence_manifest_entries": 15

  },

  "schema": "VR-2026.1"

}

Mock gates (18 total):

G.REPO.001 PASS, G.REPO.002 PASS, G.REPO.003 PASS,

G.DET.001 ASSUMED, G.DET.002 PASS,

G.SEC.001 PASS, G.SEC.002 PASS, G.SEC.003 PASS,

G.RELEASE.001 PASS, G.RELEASE.002 PASS, G.RELEASE.003 PASS,

[G.CI](http://G.CI).001 PASS,

G.OPS.001 PASS, G.OPS.002 PASS, G.OPS.003 PASS,

G.CANARY.001 PASS, G.CANARY.002 PASS,

[G.FINAL](http://G.FINAL).001 PASS

─── LAYOUT ────────────────────────────────────────────────────────────────────

TOPBAR (fixed 48px):

[AXL ◈ animated hex] ──── [repo: Agent-X-Lab] ──── [● LIVE] [⚙]

bg: --bg-void, 1px bottom border --border-dim

3-COLUMN GRID:

COL 1 — SYSTEM STATE (280px, fixed):

- VR STATUS: large text, --signal-pass, pulsing when RUN

- WORK ID: 16-char hex, --text-secondary

- UTC: timestamp

- PASS RATE: percentage

- BLOCKERS: green when 0, red with count when >0

- DETERMINISM: always --signal-assumed + ⚠ when ASSUMED_SINGLE_RUN, never green

- Divider line

- METRICS section: baseline_pass, catalog_ok, evidence_entries

COL 2 — PIPELINE MONITOR (flex):

ARA-LOOP VISUALIZER (centerpiece):

Four hexagonal SVG nodes in horizontal flow with connecting animated lines:

[PRE-LOGIC] →→→ [EXECUTOR] →→→ [ARA-LOOP] →→→ [AUDITOR]

  thinking        codex          CI logs         post-audit

Node size: 80×92px. Active: glow border --signal-pass. Done: solid green. Failed: red + shake. Pending: dim breathing.

PHASE PROGRESS BAR below nodes:

PHASE 0 ●── PHASE 1 ●── PHASE 2 ●── PHASE 3 ○── PHASE 4 ○── PHASE 5

BASELINE   SECURITY   RELEASE    OPS       CANARY     LAUNCH

Completed: filled dot green. Current: animated pulse. Future: empty dim circle.

GATE TABLE below phases:

Columns: GATE ID | STATUS | TOOL | ELAPSED

Sort order: FAIL first → ASSUMED → PASS

StatusPill component: colored pill per status

Click row → expands 200px log panel (bg #080810, 11px --signal-pass text)

GATE IDs: G.REPO.001 through [G.FINAL](http://G.FINAL).001

COL 3 — EVIDENCE FEED (320px, fixed):

Real-time artifact stream, new entries slide from top

Each entry: colored dot + timestamp + type + STATUS

SHA hash below in --text-dim

Click → shows full artifact path

PR TRACKER below feed:

Each PR: number badge + check count + title

Click → opens GitHub PR in new tab

BOTTOMBAR (fixed 40px):

[OBSERVE] [SPECIFY] [EXECUTE] [PROVE] — phase pills, active highlighted

N=3 iter | SHA: e0371af1 | 2026-02-22T18:16Z

─── COMPONENTS ────────────────────────────────────────────────────────────────

StatusPill:

- PASS: bg #00e87a15, text #00e87a, border #00e87a40

- FAIL: bg #ff2d5515, text #ff2d55, border #ff2d5540

- RUNNING: bg #4488ff15, text #4488ff, animated border

- ASSUMED: bg #aa66ff15, text #aa66ff, border #aa66ff40

- PENDING: bg #33334815, text #666688, border #333348

NodeHex: SVG hexagon clip-path, props: role/status/isActive/label

GateRow: expandable, log panel below on click

─── GITHUB API INTEGRATION ─────────────────────────────────────────────────────

Settings drawer (slide from right):

- Repo owner + repo name input (no PAT — auth is server-side in BFF Worker)

- owner/repo field

- Poll interval selector (30s default)

- Test Connection button + last verified timestamp

Hooks:

useGitHubAPI — polling 30s, manual refresh, rate limit countdown

useVRJson — GET /repos/{owner}/{repo}/contents/VR.json → base64 decode → parse

useGateStatus — GET /repos/{owner}/{repo}/actions/runs/{id}/jobs → map to gate IDs

Endpoints:

GET /repos/{owner}/{repo}/actions/runs → CI pipeline status

GET /repos/{owner}/{repo}/pulls → PR tracker

GET /repos/{owner}/{repo}/contents/VR.json → System State

GET /repos/{owner}/{repo}/contents/MANIFEST.json → Evidence Feed

GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs → Gate results

─── ERROR STATES ───────────────────────────────────────────────────────────────

BFF unreachable or owner/repo not set: centered "CONNECT REPOSITORY" form (owner + repo only; no PAT field)

Rate limit: countdown timer to reset

FAIL gate detected: full-width red banner, gate ID + link to CI run

VR status ≠ RUN: amber banner + blockers list

API failure: explicit ERROR state — never show stale data silently

─── ABSOLUTE CONSTRAINTS ───────────────────────────────────────────────────────

- Zero mock data in production build — real API or explicit NO DATA

- DETERMINISM: ASSUMED_SINGLE_RUN = always --signal-assumed + ⚠, never --signal-pass

- No Bootstrap, no shadcn defaults, no Tailwind rounded-xl

- No Inter, Roboto, system fonts — JetBrains Mono only

- No purple gradients on dark backgrounds

- No decorative elements without engineering function

- Aria-labels on all colored status indicators

- Fail-closed: ambiguity = ERROR state, not silent fallback