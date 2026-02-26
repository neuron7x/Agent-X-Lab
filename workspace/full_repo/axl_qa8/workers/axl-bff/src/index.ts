/**
 * AXL-BFF — Cloudflare Worker
 * Server-side proxy for GitHub API, KV caching, webhook invalidation,
 * engine dispatch. Browser NEVER gets a token.
 *
 * Endpoints:
 *   GET  /healthz
 *   GET  /vr
 *   POST /dispatch/run-engine
 *   GET  /gh/*              (allowlist proxy)
 *   POST /webhook/github
 */

export interface Env {
  AXL_KV: KVNamespace;
  GITHUB_TOKEN: string;
  WEBHOOK_SECRET: string;
  ALLOWED_ORIGINS: string;
  GITHUB_OWNER: string;
  GITHUB_REPO: string;
  GITHUB_VR_BRANCH: string;
  GITHUB_VR_PATH: string;
  KV_TTL_SEC: string;
  WORKER_VERSION: string;
  KV_INDEX_KEY: string;
  // Auth
  AXL_API_KEY: string; // shared key for protected endpoints (dispatch/forge); prefer Cloudflare Access for real auth
  // Prompt Forge — Claude (Anthropic)
  ANTHROPIC_API_KEY: string;
  FORGE_MODEL: string;        // optional override, default: claude-sonnet-4-6
  FORGE_MAX_TOKENS: string;   // optional override, default: 4096
  // Prompt Forge — GPT-5.2 (OpenAI)
  OPENAI_API_KEY: string;
  OPENAI_MODEL: string;       // optional override, default: gpt-5.2
  OPENAI_MAX_TOKENS: string;  // optional override, default: 4096
  // Prompt Forge — n8n
  N8N_WEBHOOK_URL: string;    // full webhook URL
  N8N_SECRET: string;         // X-N8N-Secret header value
}

// ── Prompt Forge — system prompt ───────────────────────────────────────────
// Lives server-side only. Never reaches the browser.
const FORGE_SYSTEM_PROMPT = `You are a Principal Prompt Engineer with deep expertise in cognitive systems, LLM orchestration, and adversarial robustness. Your sole function is to synthesize the user\'s raw intent into production-grade prompts or prompt bundles.

OPERATING RULES:
1. Extract the real intent even from vague or incomplete descriptions — ask ONE clarifying question maximum if truly blocked, otherwise proceed.
2. Output is ALWAYS structured. Never free-form prose without clear section headers.
3. Calibrate depth to declared expertise — if the user signals technical background, skip hand-holding; if not, add operational context.
4. Every generated prompt must contain: role definition, behavioral constraints, output contract, and at least one anti-pattern guard.
5. For bundles: produce discrete, composable prompts — each independently runnable but designed to chain.

OUTPUT MODES:
- SINGLE: One master system prompt. Dense, complete, production-ready.
- BUNDLE: Structured packet with labeled sections:
  [SYSTEM_PROMPT] — the core identity and operating contract
  [USER_TEMPLATE] — parameterized template with {variables} for the caller
  [EXAMPLES] — 2-3 few-shot examples showing correct input/output behavior
  [ANTI_PATTERNS] — explicit list of failure modes this prompt guards against
  [CHAIN_NOTES] — how to compose this with other agents/prompts if applicable

QUALITY GATES before output:
- Would a senior engineer trust this prompt in CI without modification?
- Does it degrade gracefully under adversarial input?
- Is the output contract unambiguous?

Language: match the user\'s language precisely. If Ukrainian — output in Ukrainian. If English — English. Mixed — match dominant language.`;

// ── Constants ──────────────────────────────────────────────────────────────

const GH_API = 'https://api.github.com';
const MAX_BODY_BYTES = 1_048_576; // 1 MB — GitHub webhooks can be large (100KB+); 25KB was too restrictive
const DEFAULT_TTL = 60;

// ── Security helpers ───────────────────────────────────────────────────────

/**
 * Verify X-AXL-Api-Key header.
 * Returns null if OK, Response if rejected.
 * If AXL_API_KEY is not configured, FAIL-CLOSED (deny all).
 */
function requireApiKey(request: Request, env: Env): Response | null {
  if (!env.AXL_API_KEY) {
    // Key not configured → deny all protected endpoints
    return new Response(JSON.stringify({ error: 'API_KEY_NOT_CONFIGURED' }), { status: 503 });
  }
  const provided = request.headers.get('X-AXL-Api-Key') ?? '';
  if (provided !== env.AXL_API_KEY) {
    return new Response(JSON.stringify({ error: 'UNAUTHORIZED' }), { status: 401 });
  }
  return null;
}

/**
 * Per-IP rate limiter using KV.
 * window: 60s, max: 20 requests per window per IP per route-group.
 * Returns null if OK, Response if rate limited.
 */
async function rateLimit(
  request: Request,
  env: Env,
  group: string,
): Promise<Response | null> {
  const ip = request.headers.get('CF-Connecting-IP') ?? 'unknown';
  const window = Math.floor(Date.now() / 60_000);
  const key = `rl:${group}:${ip}:${window}`;

  let count = 0;
  try {
    const val = await env.AXL_KV.get(key);
    count = val ? parseInt(val, 10) : 0;
  } catch { /* KV unavailable — fail open */ return null; }

  const MAX = 20; // per 60s window
  if (count >= MAX) {
    return new Response(JSON.stringify({ error: 'RATE_LIMITED', retry_after: 60 }), {
      status: 429,
      headers: { 'Retry-After': '60' },
    });
  }

  try {
    await env.AXL_KV.put(key, String(count + 1), { expirationTtl: 120 });
  } catch { /* non-fatal */ }

  return null;
}



// Allowlisted GitHub API path prefixes (deny-by-default proxy)
const GH_ALLOWED_PREFIXES: readonly string[] = [
  '/repos/{owner}/{repo}/contents/',
  '/repos/{owner}/{repo}/actions/runs',
  '/repos/{owner}/{repo}/actions/runs/', // job sub-paths
  '/repos/{owner}/{repo}/pulls',
  '/repos/{owner}/{repo}/commits/',
  '/repos/{owner}/{repo}',            // repo metadata
];

// ── Helpers ────────────────────────────────────────────────────────────────

function getAllowedOrigins(env: Env): string[] {
  return env.ALLOWED_ORIGINS
    ? env.ALLOWED_ORIGINS.split(',').map((s) => s.trim()).filter(Boolean)
    : [];
}

function getCorsHeaders(request: Request, env: Env): Record<string, string> {
  const origin = request.headers.get('Origin') ?? '';
  const allowed = getAllowedOrigins(env);

  // FAIL-CLOSED: if no allowed origins configured, deny ALL cross-origin requests.
  // This prevents accidental open-CORS on misconfigured deployments.
  if (!allowed.length) return {};

  // Only emit CORS headers for explicitly allowed origins.
  if (!allowed.includes(origin)) return {};

  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-AXL-Api-Key',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}

function corsResponse(request: Request, env: Env, body: string, status: number, extra?: Record<string, string>): Response {
  return new Response(body, {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...getCorsHeaders(request, env),
      ...(extra ?? {}),
    },
  });
}

function json(data: unknown, status = 200, extra?: Record<string, string>): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...(extra ?? {}) },
  });
}

function err(msg: string, status: number): Response {
  return json({ error: msg }, status);
}

function ghHeaders(token: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
    Accept: 'application/vnd.github.v3+json',
    'User-Agent': 'axl-bff/1.0',
  };
}

function kvTtl(env: Env): number {
  const t = parseInt(env.KV_TTL_SEC ?? String(DEFAULT_TTL), 10);
  return isNaN(t) || t < 1 ? DEFAULT_TTL : t;
}

function vrCacheKey(env: Env): string {
  return `vr:${env.GITHUB_OWNER}/${env.GITHUB_REPO}:${env.GITHUB_VR_BRANCH ?? 'vr-state'}`;
}

async function kvIndexAdd(kv: KVNamespace, indexKey: string, cacheKey: string): Promise<void> {
  const raw = await kv.get(indexKey);
  const set: string[] = raw ? JSON.parse(raw) : [];
  if (!set.includes(cacheKey)) {
    set.push(cacheKey);
    // Index itself has no TTL — it's a mutable set
    await kv.put(indexKey, JSON.stringify(set));
  }
}

async function kvInvalidateByPrefix(kv: KVNamespace, indexKey: string, prefix: string): Promise<number> {
  const raw = await kv.get(indexKey);
  if (!raw) return 0;
  const set: string[] = JSON.parse(raw);
  const toDelete = set.filter((k) => k.startsWith(prefix));
  await Promise.all(toDelete.map((k) => kv.delete(k)));
  const remaining = set.filter((k) => !k.startsWith(prefix));
  await kv.put(indexKey, JSON.stringify(remaining));
  return toDelete.length;
}

// ── HMAC Webhook Verification ──────────────────────────────────────────────

async function verifyWebhookSignature(secret: string, body: string, sigHeader: string | null): Promise<boolean> {
  if (!sigHeader?.startsWith('sha256=')) return false;
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const mac = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  const computed = 'sha256=' + Array.from(new Uint8Array(mac)).map((b) => b.toString(16).padStart(2, '0')).join('');
  // Constant-time comparison
  if (computed.length !== sigHeader.length) return false;
  let diff = 0;
  for (let i = 0; i < computed.length; i++) {
    diff |= computed.charCodeAt(i) ^ sigHeader.charCodeAt(i);
  }
  return diff === 0;
}

// ── GitHub proxy allowlist ─────────────────────────────────────────────────

function buildOwnerRepoPath(env: Env): string {
  return `/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}`;
}

function isAllowedGhPath(path: string, env: Env): boolean {
  const base = buildOwnerRepoPath(env);
  const allowed = [
    `${base}/contents/`,
    `${base}/actions/runs`,
    `${base}/pulls`,
    `${base}/commits/`,
    base,             // exact match for repo metadata
  ];
  // Allow repo metadata (exact or trailing slash)
  if (path === base || path === base + '/') return true;
  return allowed.slice(0, -1).some((prefix) => path.startsWith(prefix));
}

// ── Route handlers ─────────────────────────────────────────────────────────

async function handleHealthz(request: Request, env: Env): Promise<Response> {
  return corsResponse(request, env, JSON.stringify({
    ok: true,
    ts: new Date().toISOString(),
    version: env.WORKER_VERSION ?? '1.0.0',
    repo: `${env.GITHUB_OWNER}/${env.GITHUB_REPO}`,
  }), 200);
}

async function handleVr(request: Request, env: Env): Promise<Response> {
  const key = vrCacheKey(env);

  // Try KV cache first
  const cached = await env.AXL_KV.get(key);
  if (cached) {
    return corsResponse(request, env, cached, 200, {
      'X-AXL-Cache': 'HIT',
      'X-AXL-Cache-Key': key,
    });
  }

  // Fetch from GitHub (S1 strategy: committed file on vr-state branch)
  const branch = env.GITHUB_VR_BRANCH ?? 'vr-state';
  const path = env.GITHUB_VR_PATH ?? 'ad2026_state/vr/latest.json';
  const url = `${GH_API}/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/contents/${path}?ref=${encodeURIComponent(branch)}`;

  let ghRes: Response;
  try {
    ghRes = await fetch(url, { headers: ghHeaders(env.GITHUB_TOKEN) });
  } catch (e) {
    return corsResponse(request, env, JSON.stringify({ error: 'UPSTREAM_FETCH_FAILED', detail: String(e) }), 502);
  }

  if (ghRes.status === 404) {
    return corsResponse(request, env, JSON.stringify({ error: 'VR_NOT_FOUND', hint: `File not found: ${path}@${branch}` }), 404);
  }
  if (!ghRes.ok) {
    return corsResponse(request, env, JSON.stringify({ error: 'GITHUB_API_ERROR', status: ghRes.status }), 502);
  }

  const contentRes = await ghRes.json() as { content?: string; encoding?: string };
  if (!contentRes.content) {
    return corsResponse(request, env, JSON.stringify({ error: 'EMPTY_CONTENT' }), 502);
  }

  // GitHub returns base64 content with newlines
  const decoded = atob(contentRes.content.replace(/\n/g, ''));
  const ttl = kvTtl(env);
  await env.AXL_KV.put(key, decoded, { expirationTtl: ttl });
  await kvIndexAdd(env.AXL_KV, env.KV_INDEX_KEY, key);

  return corsResponse(request, env, decoded, 200, {
    'X-AXL-Cache': 'MISS',
    'X-AXL-Cache-Key': key,
    'X-AXL-TTL': String(ttl),
  });
}

async function handleDispatchRunEngine(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return corsResponse(request, env, JSON.stringify({ error: 'METHOD_NOT_ALLOWED' }), 405);
  }

  // Parse optional client payload (inputs forwarded to workflow)
  let clientPayload: Record<string, unknown> = {};
  try {
    const body = await request.text();
    if (body) clientPayload = JSON.parse(body);
  } catch { /* ignore parse errors — use empty payload */ }

  const url = `${GH_API}/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/dispatches`;
  const payload = {
    event_type: 'run-engine',
    client_payload: {
      triggered_by: 'axl-bff',
      ts: new Date().toISOString(),
      ...clientPayload,
    },
  };

  let ghRes: Response;
  try {
    ghRes = await fetch(url, {
      method: 'POST',
      headers: { ...ghHeaders(env.GITHUB_TOKEN), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    return corsResponse(request, env, JSON.stringify({ error: 'DISPATCH_FAILED', detail: String(e) }), 502);
  }

  // GitHub returns 204 on success for repository_dispatch
  if (ghRes.status === 204) {
    return corsResponse(request, env, JSON.stringify({ ok: true, dispatched: 'run-engine', ts: payload.client_payload.ts }), 202);
  }
  if (ghRes.status === 404) {
    return corsResponse(request, env, JSON.stringify({ error: 'REPO_NOT_FOUND_OR_NO_PERMISSION' }), 404);
  }
  const detail = await ghRes.text();
  return corsResponse(request, env, JSON.stringify({ error: 'GITHUB_DISPATCH_ERROR', status: ghRes.status, detail }), 502);
}

async function handleGhProxy(request: Request, env: Env, urlPath: string): Promise<Response> {
  // urlPath = everything after /gh, e.g. /repos/owner/repo/pulls
  if (!isAllowedGhPath(urlPath, env)) {
    return corsResponse(request, env, JSON.stringify({
      error: 'PROXY_PATH_DENIED',
      path: urlPath,
      hint: 'Only allowlisted GitHub API paths are accessible',
    }), 403);
  }

  // Reconstruct query string
  const reqUrl = new URL(request.url);
  const qs = reqUrl.search; // includes leading ?
  const targetUrl = `${GH_API}${urlPath}${qs}`;

  // Check KV cache for GET requests
  const cacheKey = `gh:${urlPath}${qs}`;
  if (request.method === 'GET') {
    const cached = await env.AXL_KV.get(cacheKey);
    if (cached) {
      return corsResponse(request, env, cached, 200, { 'X-AXL-Cache': 'HIT' });
    }
  }

  let ghRes: Response;
  try {
    ghRes = await fetch(targetUrl, {
      method: request.method,
      headers: ghHeaders(env.GITHUB_TOKEN),
    });
  } catch (e) {
    return corsResponse(request, env, JSON.stringify({ error: 'PROXY_FETCH_FAILED', detail: String(e) }), 502);
  }

  const body = await ghRes.text();

  if (ghRes.ok && request.method === 'GET') {
    const ttl = kvTtl(env);
    await env.AXL_KV.put(cacheKey, body, { expirationTtl: ttl });
    await kvIndexAdd(env.AXL_KV, env.KV_INDEX_KEY, cacheKey);
  }

  return corsResponse(request, env, body, ghRes.status, {
    'X-AXL-Cache': 'MISS',
    'X-AXL-GH-Status': String(ghRes.status),
  });
}

async function handleWebhook(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') return err('METHOD_NOT_ALLOWED', 405);

  // Reject oversized bodies
  const contentLength = parseInt(request.headers.get('Content-Length') ?? '0', 10);
  if (contentLength > MAX_BODY_BYTES) return err('BODY_TOO_LARGE', 413);

  const body = await request.text();
  if (body.length > MAX_BODY_BYTES) return err('BODY_TOO_LARGE', 413);

  // Verify HMAC
  const sig = request.headers.get('X-Hub-Signature-256');
  const valid = await verifyWebhookSignature(env.WEBHOOK_SECRET, body, sig);
  if (!valid) {
    // Log minimal info only (no secrets)
    console.warn('[webhook] signature verification failed');
    return err('SIGNATURE_INVALID', 401);
  }

  const event = request.headers.get('X-GitHub-Event') ?? 'unknown';

  let payload: { repository?: { full_name?: string }; ref?: string; workflow_run?: { head_branch?: string } } = {};
  try {
    payload = JSON.parse(body);
  } catch {
    return err('INVALID_JSON', 400);
  }

  const repoFullName = payload?.repository?.full_name ?? '';
  const ref = payload?.ref ?? payload?.workflow_run?.head_branch ?? '';

  // Minimal logging — NO secrets, NO payload content
  console.log(`[webhook] event=${event} repo=${repoFullName} ref=${ref}`);

  // Invalidate KV on relevant events
  const invalidateEvents = ['push', 'workflow_run', 'repository_dispatch'];
  if (invalidateEvents.includes(event)) {
    const prefix = `vr:${repoFullName}`;
    const deleted = await kvInvalidateByPrefix(env.AXL_KV, env.KV_INDEX_KEY, prefix);
    // Also invalidate gh proxy cache for this repo
    const ghPrefix = `gh:/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}`;
    const ghDeleted = await kvInvalidateByPrefix(env.AXL_KV, env.KV_INDEX_KEY, ghPrefix);
    console.log(`[webhook] invalidated ${deleted} vr keys, ${ghDeleted} gh keys`);
    return json({ ok: true, event, invalidated: deleted + ghDeleted });
  }

  return json({ ok: true, event, action: 'noop' });
}


// ── Prompt Forge handler ───────────────────────────────────────────────────

interface ForgeMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ForgeRequest {
  messages: ForgeMessage[];
  mode?: 'single' | 'bundle';
  model?: string;
}

async function handleForge(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return corsResponse(request, env, JSON.stringify({ error: 'METHOD_NOT_ALLOWED' }), 405);
  }

  if (!env.ANTHROPIC_API_KEY) {
    return corsResponse(request, env, JSON.stringify({ error: 'FORGE_NOT_CONFIGURED', hint: 'Set ANTHROPIC_API_KEY Worker secret' }), 503);
  }

  // Parse body
  let body: string;
  try {
    body = await request.text();
    if (body.length > 32_768) {
      return corsResponse(request, env, JSON.stringify({ error: 'BODY_TOO_LARGE' }), 413);
    }
  } catch {
    return corsResponse(request, env, JSON.stringify({ error: 'BODY_READ_FAILED' }), 400);
  }

  let req: ForgeRequest;
  try {
    req = JSON.parse(body);
  } catch {
    return corsResponse(request, env, JSON.stringify({ error: 'INVALID_JSON' }), 400);
  }

  if (!Array.isArray(req.messages) || req.messages.length === 0) {
    return corsResponse(request, env, JSON.stringify({ error: 'MESSAGES_REQUIRED' }), 400);
  }

  // Validate messages
  for (const m of req.messages) {
    if (!m.role || !m.content || typeof m.content !== 'string') {
      return corsResponse(request, env, JSON.stringify({ error: 'INVALID_MESSAGE_FORMAT' }), 400);
    }
    if (m.role !== 'user' && m.role !== 'assistant') {
      return corsResponse(request, env, JSON.stringify({ error: 'INVALID_MESSAGE_ROLE', role: m.role }), 400);
    }
  }

  const model = req.model || env.FORGE_MODEL || 'claude-sonnet-4-6';
  const maxTokens = parseInt(env.FORGE_MAX_TOKENS || '4096', 10);
  const mode = req.mode ?? 'single';

  // Inject mode hint into last user message if not already present
  const messages = [...req.messages];
  const lastUserIdx = [...messages].reverse().findIndex(m => m.role === 'user');
  if (lastUserIdx !== -1) {
    const idx = messages.length - 1 - lastUserIdx;
    const modeHint = mode === 'bundle'
      ? '\n\n[OUTPUT_MODE: BUNDLE — produce the full structured packet with all sections]'
      : '\n\n[OUTPUT_MODE: SINGLE — produce one complete system prompt]';
    messages[idx] = {
      ...messages[idx],
      content: messages[idx].content + modeHint,
    };
  }

  // Call Anthropic API with streaming
  let anthropicRes: Response;
  try {
    anthropicRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'anthropic-beta': 'messages-2023-12-15',
      },
      body: JSON.stringify({
        model,
        max_tokens: maxTokens,
        system: FORGE_SYSTEM_PROMPT,
        messages,
        stream: true,
      }),
    });
  } catch (e) {
    return corsResponse(request, env, JSON.stringify({ error: 'ANTHROPIC_FETCH_FAILED', detail: String(e) }), 502);
  }

  if (!anthropicRes.ok) {
    const errText = await anthropicRes.text();
    return corsResponse(request, env, JSON.stringify({
      error: 'ANTHROPIC_API_ERROR',
      status: anthropicRes.status,
      detail: errText.slice(0, 500),
    }), anthropicRes.status);
  }

  // Stream SSE response directly to client
  const corsHeaders = getCorsHeaders(request, env);
  return new Response(anthropicRes.body, {
    status: 200,
    headers: {
      ...corsHeaders,
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    },
  });
}


// ── FORGE SYSTEM PROMPT (shared across all providers) ─────────────────────
// Defined once, reused by Claude / GPT-5.2 / n8n

// ── GPT-5.2 Forge handler ─────────────────────────────────────────────────
// POST /ai/forge/gpt
// Calls api.openai.com/v1/chat/completions with stream:true
// SSE format differs from Anthropic: data: {"choices":[{"delta":{"content":"..."}}]}

interface GptForgeRequest {
  messages: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>;
  mode?: 'single' | 'bundle';
  model?: string;
}

async function handleForgeGPT(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return corsResponse(request, env, JSON.stringify({ error: 'METHOD_NOT_ALLOWED' }), 405);
  }
  if (!env.OPENAI_API_KEY) {
    return corsResponse(request, env, JSON.stringify({ error: 'GPT_NOT_CONFIGURED', hint: 'Set OPENAI_API_KEY Worker secret' }), 503);
  }

  let body: string;
  try {
    body = await request.text();
    if (body.length > 32_768) return corsResponse(request, env, JSON.stringify({ error: 'BODY_TOO_LARGE' }), 413);
  } catch {
    return corsResponse(request, env, JSON.stringify({ error: 'BODY_READ_FAILED' }), 400);
  }

  let req: GptForgeRequest;
  try { req = JSON.parse(body); } catch {
    return corsResponse(request, env, JSON.stringify({ error: 'INVALID_JSON' }), 400);
  }
  if (!Array.isArray(req.messages) || req.messages.length === 0) {
    return corsResponse(request, env, JSON.stringify({ error: 'MESSAGES_REQUIRED' }), 400);
  }

  const model = req.model || env.OPENAI_MODEL || 'gpt-5.2';
  const maxTokens = parseInt(env.OPENAI_MAX_TOKENS || '4096', 10);
  const mode = req.mode ?? 'single';

  const modeHint = mode === 'bundle'
    ? '\n\n[OUTPUT_MODE: BUNDLE — produce the full structured packet with all sections]'
    : '\n\n[OUTPUT_MODE: SINGLE — produce one complete system prompt]';

  // Build messages: system prompt first, then user messages with mode hint injected
  const messages: GptForgeRequest['messages'] = [
    { role: 'system', content: FORGE_SYSTEM_PROMPT },
    ...req.messages,
  ];
  // Inject mode hint into last user message
  const lastIdx = [...messages].reverse().findIndex(m => m.role === 'user');
  if (lastIdx !== -1) {
    const idx = messages.length - 1 - lastIdx;
    messages[idx] = { ...messages[idx], content: messages[idx].content + modeHint };
  }

  let openaiRes: Response;
  try {
    openaiRes = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model,
        max_tokens: maxTokens,
        messages,
        stream: true,
      }),
    });
  } catch (e) {
    return corsResponse(request, env, JSON.stringify({ error: 'OPENAI_FETCH_FAILED', detail: String(e) }), 502);
  }

  if (!openaiRes.ok) {
    const errText = await openaiRes.text();
    return corsResponse(request, env, JSON.stringify({
      error: 'OPENAI_API_ERROR',
      status: openaiRes.status,
      detail: errText.slice(0, 500),
    }), openaiRes.status);
  }

  // Stream SSE directly to client — same content-type, different delta format
  const corsHeaders = getCorsHeaders(request, env);
  return new Response(openaiRes.body, {
    status: 200,
    headers: {
      ...corsHeaders,
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
      'X-Forge-Provider': 'openai',
      'X-Forge-Model': model,
    },
  });
}

// ── n8n Forge handler ─────────────────────────────────────────────────────
// POST /ai/forge/n8n
// Sends user input to n8n webhook, returns JSON (n8n does not stream).
// n8n workflow handles: intent classification → model routing → prompt generation.
// Worker wraps response as a single SSE event for UI compatibility.

interface N8nForgeRequest {
  messages: Array<{ role: 'user' | 'assistant'; content: string }>;
  mode?: 'single' | 'bundle';
}

async function handleForgeN8n(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return corsResponse(request, env, JSON.stringify({ error: 'METHOD_NOT_ALLOWED' }), 405);
  }
  if (!env.N8N_WEBHOOK_URL) {
    return corsResponse(request, env, JSON.stringify({ error: 'N8N_NOT_CONFIGURED', hint: 'Set N8N_WEBHOOK_URL Worker secret' }), 503);
  }

  let body: string;
  try {
    body = await request.text();
    if (body.length > 32_768) return corsResponse(request, env, JSON.stringify({ error: 'BODY_TOO_LARGE' }), 413);
  } catch {
    return corsResponse(request, env, JSON.stringify({ error: 'BODY_READ_FAILED' }), 400);
  }

  let req: N8nForgeRequest;
  try { req = JSON.parse(body); } catch {
    return corsResponse(request, env, JSON.stringify({ error: 'INVALID_JSON' }), 400);
  }
  if (!Array.isArray(req.messages) || req.messages.length === 0) {
    return corsResponse(request, env, JSON.stringify({ error: 'MESSAGES_REQUIRED' }), 400);
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (env.N8N_SECRET) headers['X-N8N-Secret'] = env.N8N_SECRET;

  let n8nRes: Response;
  try {
    n8nRes = await fetch(env.N8N_WEBHOOK_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        messages: req.messages,
        mode: req.mode ?? 'single',
        // Pass system prompt so n8n workflow can use or override it
        systemPrompt: FORGE_SYSTEM_PROMPT,
      }),
    });
  } catch (e) {
    return corsResponse(request, env, JSON.stringify({ error: 'N8N_FETCH_FAILED', detail: String(e) }), 502);
  }

  if (!n8nRes.ok) {
    const errText = await n8nRes.text();
    return corsResponse(request, env, JSON.stringify({
      error: 'N8N_WEBHOOK_ERROR',
      status: n8nRes.status,
      detail: errText.slice(0, 500),
    }), n8nRes.status);
  }

  // n8n returns JSON — expected shape: { content: string } or { prompts: string[] }
  // Wrap as a single SSE event so UI can use the same stream reader
  let n8nData: unknown;
  try { n8nData = await n8nRes.json(); } catch {
    return corsResponse(request, env, JSON.stringify({ error: 'N8N_INVALID_JSON' }), 502);
  }

  const content = typeof (n8nData as Record<string, unknown>).content === 'string'
    ? (n8nData as Record<string, unknown>).content as string
    : JSON.stringify(n8nData);

  // Emit as Anthropic-compatible SSE so UI reuses same stream parser
  const sseBody = [
    `data: ${JSON.stringify({ type: 'content_block_delta', delta: { type: 'text_delta', text: content } })}`,
    `data: ${JSON.stringify({ type: 'message_stop' })}`,
    '',
  ].join('\n\n');

  const corsHeaders = getCorsHeaders(request, env);
  return new Response(sseBody, {
    status: 200,
    headers: {
      ...corsHeaders,
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Forge-Provider': 'n8n',
    },
  });
}

// ── Main fetch handler ─────────────────────────────────────────────────────

export default {
  async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const { pathname } = url;

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: getCorsHeaders(request, env),
      });
    }

    // Route
    if (pathname === '/healthz') return handleHealthz(request, env);
    if (pathname === '/vr') return handleVr(request, env);
    if (pathname === '/dispatch/run-engine') {
      const authErr = requireApiKey(request, env);
      if (authErr) return authErr;
      const rlErr = await rateLimit(request, env, 'dispatch');
      if (rlErr) return rlErr;
      return handleDispatchRunEngine(request, env);
    }
    if (pathname.startsWith('/gh/')) {
      // SECURITY: /gh proxy is GET/HEAD only — fail-closed
      if (request.method !== 'GET' && request.method !== 'HEAD') {
        return corsResponse(request, env, JSON.stringify({ error: 'METHOD_NOT_ALLOWED', hint: '/gh proxy accepts GET/HEAD only' }), 405);
      }
      const ghPath = pathname.slice('/gh'.length); // keep leading /
      return handleGhProxy(request, env, ghPath);
    }
    if (pathname === '/webhook/github') return handleWebhook(request, env);
    if (pathname === '/ai/forge' || pathname === '/ai/forge/gpt' || pathname === '/ai/forge/n8n') {
      const authErr = requireApiKey(request, env);
      if (authErr) return authErr;
      const rlErr = await rateLimit(request, env, 'forge');
      if (rlErr) return rlErr;
      if (pathname === '/ai/forge') return handleForge(request, env);
      if (pathname === '/ai/forge/gpt') return handleForgeGPT(request, env);
      return handleForgeN8n(request, env);
    }

    return corsResponse(request, env, JSON.stringify({ error: 'NOT_FOUND', path: pathname }), 404);
  },
};
