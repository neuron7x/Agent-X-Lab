/**
 * AXL API client — all requests go through the BFF Worker.
 * Zero direct calls to api.github.com from the browser.
 *
 * Base URL: VITE_AXL_API_BASE env var (required in production)
 * Fallback:  http://localhost:8787 for local Worker dev
 */

import type { VRData, EvidenceEntry, PullRequest, Gate, ArsenalPrompt, ContractJson, GateStatus } from './types';

// ── Config ─────────────────────────────────────────────────────────────────

export function getApiBase(): string {
  // Vite exposes VITE_* vars via import.meta.env
  const base = (import.meta.env?.VITE_AXL_API_BASE as string | undefined) ?? '';
  if (!base) {
    if (import.meta.env?.DEV) {
      console.warn('[axl-api] VITE_AXL_API_BASE not set — falling back to http://localhost:8787');
      return 'http://localhost:8787';
    }
    throw new Error('VITE_AXL_API_BASE is not configured. Set it in your Vercel project environment variables.');
  }
  return base.replace(/\/$/, '');
}

function getApiKey(): string {
  return (import.meta.env?.VITE_AXL_API_KEY as string | undefined) ?? '';
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface ApiError {
  code: string;
  status: number;
  message: string;
  retryAfter?: number;
}

export class AXLApiError extends Error {
  code: string;
  status: number;
  retryAfter?: number;
  constructor(err: ApiError) {
    super(err.message);
    this.name = 'AXLApiError';
    this.code = err.code;
    this.status = err.status;
    this.retryAfter = err.retryAfter;
  }
}

// ── Core fetch with retry ──────────────────────────────────────────────────

const RETRY_STATUS = new Set([429, 500, 502, 503, 504]);
const RETRY_DELAYS_MS = [1000, 2000, 4000];

async function apiFetch(path: string, init?: RequestInit, attempt = 0): Promise<Response> {
  const url = `${getApiBase()}${path}`;
  let res: Response;
  try {
    res = await fetch(url, { ...init, credentials: 'omit' });
  } catch (networkErr) {
    if (attempt < RETRY_DELAYS_MS.length) {
      await delay(RETRY_DELAYS_MS[attempt]);
      return apiFetch(path, init, attempt + 1);
    }
    throw new AXLApiError({ code: 'NETWORK_ERROR', status: 0, message: String(networkErr) });
  }

  if (RETRY_STATUS.has(res.status) && attempt < RETRY_DELAYS_MS.length) {
    const retryAfter = parseInt(res.headers.get('Retry-After') ?? '0', 10);
    await delay(retryAfter > 0 ? retryAfter * 1000 : RETRY_DELAYS_MS[attempt]);
    return apiFetch(path, init, attempt + 1);
  }

  return res;
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function parseOrThrow<T>(res: Response, context: string): Promise<T> {
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    throw new AXLApiError({ code: 'PARSE_ERROR', status: res.status, message: `Failed to parse response from ${context}` });
  }
  if (!res.ok) {
    const errBody = body as Record<string, unknown>;
    const retryAfter = errBody?.retry_after as number | undefined;
    throw new AXLApiError({
      code: (errBody?.error as string) ?? `HTTP_${res.status}`,
      status: res.status,
      message: (errBody?.hint as string) ?? (errBody?.detail as string) ?? `Request failed: ${context}`,
      retryAfter,
    });
  }
  return body as T;
}

// ── Public API ─────────────────────────────────────────────────────────────

/**
 * Health check — verify BFF is reachable
 */
export async function healthz(): Promise<{ ok: boolean; ts: string; version: string }> {
  const res = await apiFetch('/healthz');
  return parseOrThrow(res, '/healthz');
}

/**
 * Fetch VR.json (cached in KV, TTL 60s)
 */
export async function fetchVRJson(): Promise<VRData> {
  const res = await apiFetch('/vr');
  return parseOrThrow<VRData>(res, '/vr');
}

/**
 * Trigger engine run via repository_dispatch
 */
export async function dispatchRunEngine(payload?: Record<string, unknown>): Promise<{ ok: boolean; dispatched: string; ts: string }> {
  const res = await apiFetch('/dispatch/run-engine', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-AXL-Api-Key': getApiKey() },
    body: payload ? JSON.stringify(payload) : '{}',
  });
  return parseOrThrow(res, '/dispatch/run-engine');
}

/**
 * Generic GitHub proxy — only allowlisted paths work.
 * path = GitHub API path starting with /repos/{owner}/{repo}/...
 */
export async function ghProxy<T = unknown>(path: string, params?: Record<string, string>): Promise<T> {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await apiFetch(`/gh${path}${qs}`);
  return parseOrThrow<T>(res, `/gh${path}`);
}

// ── Domain-specific helpers ────────────────────────────────────────────────

export interface GitHubSettings {
  owner: string;
  repo: string;
  token?: string; // ignored — kept for type compatibility during migration
  pollInterval: number;
}

/** Fetch repo metadata */
export async function fetchRepoInfo(settings: GitHubSettings): Promise<unknown> {
  return ghProxy(`/repos/${settings.owner}/${settings.repo}`);
}

/** Test connection — uses /healthz + /vr availability */
export async function testConnection(_settings: GitHubSettings): Promise<boolean> {
  try {
    await healthz();
    return true;
  } catch {
    return false;
  }
}

/** Fetch raw text file via proxy */
export async function fetchContentsText(settings: GitHubSettings, path: string): Promise<string> {
  const data = await ghProxy<{ content?: string; encoding?: string }>(
    `/repos/${settings.owner}/${settings.repo}/contents/${path}`
  );
  if (!data.content) throw new AXLApiError({ code: 'EMPTY_CONTENT', status: 200, message: `Empty content: ${path}` });
  return atob(data.content.replace(/\n/g, ''));
}

/** Fetch and parse JSON file */
export async function fetchContentsJson<T = unknown>(settings: GitHubSettings, path: string): Promise<T> {
  const text = await fetchContentsText(settings, path);
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new AXLApiError({ code: 'PARSE_ERROR', status: 200, message: `JSON parse failed: ${path}` });
  }
}

/** Fetch VR.json through BFF cache */
export async function fetchVRJsonSettings(_settings: GitHubSettings): Promise<VRData> {
  return fetchVRJson();
}

/** Fetch contract.json */
export async function fetchContract(settings: GitHubSettings): Promise<ContractJson> {
  return fetchContentsJson<ContractJson>(settings, 'artifacts/agent/contract.json');
}

// ── Evidence parsing (pure, kept identical to original) ──────────────────

interface EvidenceEvent {
  ts?: string; utc?: string; id?: string; command?: string;
  exit?: number; status?: string; path?: string; sha?: string;
  [key: string]: unknown;
}

export function parseEvidenceLines(text: string): { entries: EvidenceEntry[]; parseFailures: number } {
  const lines = text.split('\n').filter((l) => l.trim());
  const entries: EvidenceEntry[] = [];
  let parseFailures = 0;
  for (const line of lines) {
    try {
      const evt: EvidenceEvent = JSON.parse(line);
      let status: GateStatus = 'ASSUMED';
      if (evt.status) {
        const s = evt.status.toUpperCase();
        if (s === 'PASS' || s === 'SUCCESS' || s === 'OK') status = 'PASS';
        else if (s === 'FAIL' || s === 'FAILURE' || s === 'ERROR') status = 'FAIL';
        else if (s === 'RUNNING') status = 'RUNNING';
        else if (s === 'PENDING') status = 'PENDING';
        else status = 'ASSUMED';
      } else if (evt.exit !== undefined) {
        status = evt.exit === 0 ? 'PASS' : 'FAIL';
      }
      entries.push({
        timestamp: evt.ts || evt.utc || '',
        type: evt.command || evt.id || '',
        status,
        sha: (evt.sha || '').slice(0, 8),
        path: evt.path || '',
      });
    } catch { parseFailures++; }
  }
  entries.reverse();
  return { entries: entries.slice(0, 30), parseFailures };
}

export async function fetchEvidenceJsonl(settings: GitHubSettings): Promise<{ entries: EvidenceEntry[]; parseFailures: number }> {
  const text = await fetchContentsText(settings, 'artifacts/agent/evidence.jsonl');
  return parseEvidenceLines(text);
}

// ── Workflow runs ──────────────────────────────────────────────────────────

export interface GitHubWorkflowRun {
  id: number; name: string; display_title: string;
  path: string; status: string; conclusion: string | null;
  head_sha: string; created_at: string;
}

export interface GitHubRunsResponse {
  total_count: number;
  workflow_runs: GitHubWorkflowRun[];
}

export async function fetchActionRuns(
  settings: GitHubSettings,
  params?: { branch?: string; per_page?: number }
): Promise<GitHubRunsResponse> {
  const pp = params?.per_page ?? 50;
  const q: Record<string, string> = { per_page: String(pp) };
  if (params?.branch) q.branch = params.branch;
  return ghProxy<GitHubRunsResponse>(`/repos/${settings.owner}/${settings.repo}/actions/runs`, q);
}

export interface GitHubJob {
  id: number; name: string; status: string;
  conclusion: string | null; started_at: string | null; completed_at: string | null;
}

export interface GitHubJobsResponse {
  total_count: number;
  jobs: GitHubJob[];
}

export async function fetchRunJobs(settings: GitHubSettings, runId: number): Promise<GitHubJob[]> {
  const data = await ghProxy<GitHubJobsResponse>(
    `/repos/${settings.owner}/${settings.repo}/actions/runs/${runId}/jobs`
  );
  return data.jobs ?? [];
}

export function mapJobToGateStatus(job: GitHubJob | null): GateStatus {
  if (!job) return 'PENDING';
  if (job.conclusion === 'success') return 'PASS';
  if (['failure', 'cancelled', 'timed_out', 'action_required'].includes(job.conclusion ?? '')) return 'FAIL';
  if (['in_progress', 'queued'].includes(job.status)) return 'RUNNING';
  return 'PENDING';
}

export function jobElapsed(job: GitHubJob | null): string {
  if (!job || !job.completed_at || !job.started_at) return '—';
  const completedAt = new Date(job.completed_at).getTime();
  const startedAt = new Date(job.started_at).getTime();
  if (!Number.isFinite(completedAt) || !Number.isFinite(startedAt)) return '—';
  const s = Math.max(0, Math.round((completedAt - startedAt) / 1000));
  return s >= 60 ? `${Math.floor(s / 60)}m${String(s % 60).padStart(2, '0')}s` : `${s}s`;
}

// ── Gate resolution ────────────────────────────────────────────────────────

async function batchMap<T, R>(items: T[], concurrency: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let idx = 0;
  async function next(): Promise<void> {
    while (idx < items.length) { const i = idx++; results[i] = await fn(items[i]); }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, () => next()));
  return results;
}

export async function resolveGatesFromContract(
  settings: GitHubSettings,
  contract: ContractJson,
  runs: GitHubWorkflowRun[]
): Promise<Gate[]> {
  const runIdSet = new Set<number>();
  const checkToRun = new Map<string, GitHubWorkflowRun>();
  for (const check of contract.required_checks) {
    const workflowName = check.name.split('/')[0];
    const matchingRun = runs.find((r) => {
      const rName = r.name || r.display_title || '';
      return rName.toLowerCase().includes(workflowName.toLowerCase()) ||
        (r.path ?? '').toLowerCase().includes(workflowName.toLowerCase());
    });
    if (matchingRun) { runIdSet.add(matchingRun.id); checkToRun.set(check.name, matchingRun); }
  }
  const runIds = Array.from(runIdSet).slice(0, 12);
  const jobResults = await Promise.allSettled(runIds.map((id) => fetchRunJobs(settings, id)));
  const jobsByRunId = new Map<number, GitHubJob[]>();
  runIds.forEach((id, i) => {
    if (jobResults[i].status === 'fulfilled') {
      jobsByRunId.set(id, (jobResults[i] as PromiseFulfilledResult<GitHubJob[]>).value);
    }
  });
  return contract.required_checks.map((check) => {
    const parts = check.name.split('/');
    const workflowName = parts[0];
    const jobName = parts.length > 1 ? parts.slice(1).join('/') : parts[0];
    const matchingRun = checkToRun.get(check.name);
    if (!matchingRun) return { id: check.name, status: 'PENDING' as GateStatus, tool: check.description || workflowName, elapsed: '—' };
    const jobs = jobsByRunId.get(matchingRun.id);
    if (!jobs) return { id: check.name, status: 'PENDING' as GateStatus, tool: check.description || workflowName, elapsed: '—', log: `Failed to fetch jobs for run ${matchingRun.id}` };
    const matchingJob = jobs.find((j) => (j.name || '').toLowerCase().includes(jobName.toLowerCase())) || jobs[0] || null;
    return {
      id: check.name, status: mapJobToGateStatus(matchingJob),
      tool: matchingJob?.name || jobName, elapsed: jobElapsed(matchingJob),
      log: matchingJob ? `[${matchingJob.name}]\nStatus: ${matchingJob.status}\nConclusion: ${matchingJob.conclusion || 'null'}` : undefined,
    };
  });
}

// ── Pull requests ──────────────────────────────────────────────────────────

interface GitHubPR { number: number; title: string; html_url: string; head: { sha: string }; }
interface GitHubCheckRunsResponse { total_count: number; check_runs: Array<{ status: string; conclusion: string | null }>; }

export async function fetchPullRequests(settings: GitHubSettings): Promise<PullRequest[]> {
  const data = await ghProxy<GitHubPR[]>(
    `/repos/${settings.owner}/${settings.repo}/pulls`,
    { state: 'open', per_page: '10' }
  );
  return batchMap(data, 4, async (pr) => {
    let checksTotal = 0, checksPassed = 0, checksFailed = 0;
    try {
      const crData = await ghProxy<GitHubCheckRunsResponse>(
        `/repos/${settings.owner}/${settings.repo}/commits/${pr.head.sha}/check-runs`,
        { per_page: '100' }
      );
      const runs = crData.check_runs ?? [];
      checksTotal = runs.length;
      checksPassed = runs.filter((cr) => cr.status === 'completed' && cr.conclusion === 'success').length;
      checksFailed = runs.filter((cr) => ['failure', 'cancelled', 'timed_out', 'action_required'].includes(cr.conclusion ?? '')).length;
    } catch { /* leave as 0 */ }
    return { number: pr.number, title: pr.title, checksTotal, checksPassed, checksFailed, url: pr.html_url };
  });
}

export async function fetchManifest(settings: GitHubSettings): Promise<EvidenceEntry[]> {
  try {
    const text = await fetchContentsText(settings, 'MANIFEST.json');
    const manifest: Array<{ timestamp?: string; utc?: string; type?: string; name?: string; status?: string; sha?: string; hash?: string; path?: string }> = JSON.parse(text);
    if (Array.isArray(manifest)) {
      return manifest.map((e) => ({
        timestamp: e.timestamp || e.utc || '',
        type: e.type || e.name || '',
        status: (e.status || 'PASS') as GateStatus,
        sha: (e.sha || e.hash || '').slice(0, 8),
        path: e.path || '',
      }));
    }
  } catch { /* ignore */ }
  return [];
}

// ── Arsenal ────────────────────────────────────────────────────────────────

import type { ArsenalRole } from './types';

function detectArsenalRole(text: string): ArsenalRole {
  const lower = text.toLowerCase();
  if (/\b(pr|orchestrator|readiness)\b/.test(lower)) return 'PR-AGENT';
  if (/\b(security|appsec|supply.chain)\b/.test(lower)) return 'SECURITY-AGENT';
  if (/\b(ci|test|flake|reliability)\b/.test(lower)) return 'CI-AGENT';
  if (/\b(docs|quickstart|onboarding)\b/.test(lower)) return 'DOCS-AGENT';
  if (/\b(science|simulation|research)\b/.test(lower)) return 'SCIENCE-AGENT';
  return 'OTHER';
}

export function parseArsenalMeta(content: string, path: string, sha: string): ArsenalPrompt {
  const lines = content.split('\n');
  const titleLine = lines.find((l) => l.startsWith('#')) || lines.find((l) => l.trim()) || path;
  const title = titleLine.replace(/^#+\s*/, '').trim();
  const versionMatch = content.match(/Version:\s*(.+)/i);
  const version = versionMatch ? versionMatch[1].trim().split(/\s*[|│]/)[0].trim() : '—';
  const targetMatch = content.match(/Target:\s*(.+)/i);
  let target = 'Universal';
  if (targetMatch) { target = targetMatch[1].trim(); }
  else {
    const cl = content.toLowerCase();
    if (cl.includes('codex') && cl.includes('claude')) target = 'Codex / Claude';
    else if (cl.includes('codex') && cl.includes('copilot')) target = 'Codex / GitHub Copilot';
    else if (cl.includes('codex')) target = 'Codex';
    else if (cl.includes('copilot')) target = 'GitHub Copilot';
    else if (cl.includes('claude')) target = 'Claude';
  }
  const role = detectArsenalRole(title + ' ' + content.slice(0, 500));
  const id = path.split('/').pop()?.replace(/\.(md|txt)$/, '') ?? sha.slice(0, 8);
  return { id, title, role, version, target, content, sha: sha.slice(0, 8), path };
}

interface GitHubDirEntry { name: string; path: string; type: string; sha: string; }

export async function fetchArsenalIndex(settings: GitHubSettings): Promise<ArsenalPrompt[]> {
  const data = await ghProxy<GitHubDirEntry[]>(
    `/repos/${settings.owner}/${settings.repo}/contents/objects`
  );
  const files = data.filter((e) => e.type === 'file' && (e.name.endsWith('.md') || e.name.endsWith('.txt')));
  const results = await Promise.allSettled(
    files.slice(0, 12).map(async (file) => {
      const content = await fetchContentsText(settings, file.path);
      return parseArsenalMeta(content, file.path, file.sha);
    })
  );
  const prompts = results
    .filter((r): r is PromiseFulfilledResult<ArsenalPrompt> => r.status === 'fulfilled')
    .map((r) => r.value);
  prompts.sort((a, b) => a.title.localeCompare(b.title));
  if (prompts.length === 0) throw new AXLApiError({ code: 'ARSENAL_EMPTY', status: 404, message: 'No protocol files found in /objects/' });
  return prompts;
}

// ── Prompt Forge ──────────────────────────────────────────────────────────

export interface ForgeMessage {
  role: 'user' | 'assistant';
  content: string;
}

export type ForgeMode = 'single' | 'bundle';
export type ForgeModel = 'claude-sonnet-4-6' | 'claude-opus-4-6' | 'claude-haiku-4-5-20251001';

export interface ForgeStreamCallbacks {
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (err: string) => void;
}

/**
 * Stream a Prompt Forge generation from the BFF.
 * Parses Anthropic SSE format and calls onToken for each delta.
 * Returns abort controller so caller can cancel.
 */
export function forgeStream(
  messages: ForgeMessage[],
  mode: ForgeMode,
  model: ForgeModel,
  callbacks: ForgeStreamCallbacks,
  endpoint: string = '/ai/forge',
): AbortController {
  const abortCtrl = new AbortController();
  const base = getApiBase();

  (async () => {
    let res: Response;
    try {
      res = await fetch(`${base}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-AXL-Api-Key': getApiKey() },
        body: JSON.stringify({ messages, mode, model }),
        signal: abortCtrl.signal,
        credentials: 'omit',
      });
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      callbacks.onError(`FETCH_FAILED: ${String(e)}`);
      return;
    }

    if (!res.ok) {
      let detail = '';
      try { detail = await res.text(); } catch { /* ignore */ }
      callbacks.onError(`HTTP_${res.status}: ${detail.slice(0, 200)}`);
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) { callbacks.onError('NO_BODY'); return; }
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      let done = false;
      let value: Uint8Array | undefined;
      try {
        ({ done, value } = await reader.read());
      } catch (e) {
        if ((e as Error).name === 'AbortError') return;
        callbacks.onError(`STREAM_READ_FAILED: ${String(e)}`);
        return;
      }

      if (done) { callbacks.onDone(); return; }
      buffer += decoder.decode(value, { stream: true });

      // Parse SSE lines
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = line.slice(6).trim();
        if (data === '[DONE]') { callbacks.onDone(); return; }
        try {
          const parsed = JSON.parse(data) as {
            type?: string;
            delta?: { type?: string; text?: string };
            error?: { message?: string };
          };
          if (parsed.type === 'content_block_delta' && parsed.delta?.type === 'text_delta') {
            callbacks.onToken(parsed.delta.text ?? '');
          }
          if (parsed.type === 'message_stop') { callbacks.onDone(); return; }
          if (parsed.type === 'error') {
            callbacks.onError(parsed.error?.message ?? 'STREAM_ERROR');
            return;
          }
        } catch { /* skip malformed SSE lines */ }
      }
    }
  })();

  return abortCtrl;
}

// ── Forge providers ────────────────────────────────────────────────────────

export type ForgeProvider = 'claude' | 'gpt' | 'n8n';

/**
 * GPT-5.2 Forge stream.
 * OpenAI SSE delta format: {"choices":[{"delta":{"content":"..."}}]}
 * Worker endpoint: POST /ai/forge/gpt
 */
export function forgeStreamGPT(
  messages: ForgeMessage[],
  mode: ForgeMode,
  callbacks: ForgeStreamCallbacks,
): AbortController {
  const abortCtrl = new AbortController();
  const base = getApiBase();

  (async () => {
    let res: Response;
    try {
      res = await fetch(`${base}/ai/forge/gpt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-AXL-Api-Key': getApiKey() },
        body: JSON.stringify({ messages, mode }),
        signal: abortCtrl.signal,
        credentials: 'omit',
      });
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      callbacks.onError(`FETCH_FAILED: ${String(e)}`);
      return;
    }

    if (!res.ok) {
      let detail = '';
      try { detail = await res.text(); } catch { /* ignore */ }
      callbacks.onError(`HTTP_${res.status}: ${detail.slice(0, 200)}`);
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) { callbacks.onError('NO_BODY'); return; }
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      let done = false;
      let value: Uint8Array | undefined;
      try {
        ({ done, value } = await reader.read());
      } catch (e) {
        if ((e as Error).name === 'AbortError') return;
        callbacks.onError(`STREAM_READ_FAILED: ${String(e)}`);
        return;
      }

      if (done) { callbacks.onDone(); return; }
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = line.slice(6).trim();
        if (data === '[DONE]') { callbacks.onDone(); return; }
        try {
          // OpenAI SSE: {"choices":[{"delta":{"content":"..."},"finish_reason":null}]}
          // BUT: Worker also proxies Anthropic-format SSE from n8n (message_stop etc.)
          const parsed = JSON.parse(data) as {
            choices?: Array<{ delta?: { content?: string }; finish_reason?: string | null }>;
            // Anthropic-compat (n8n fallback via /ai/forge/gpt route)
            type?: string;
            delta?: { type?: string; text?: string };
          };

          // OpenAI format
          if (parsed.choices?.[0]?.delta?.content) {
            callbacks.onToken(parsed.choices[0].delta.content);
          }
          if (parsed.choices?.[0]?.finish_reason === 'stop') {
            callbacks.onDone(); return;
          }
          // Anthropic-compat fallback (same parser used by Anthropic forge)
          if (parsed.type === 'content_block_delta' && parsed.delta?.type === 'text_delta') {
            callbacks.onToken(parsed.delta.text ?? '');
          }
          if (parsed.type === 'message_stop') { callbacks.onDone(); return; }
        } catch { /* skip malformed */ }
      }
    }
  })();

  return abortCtrl;
}

/**
 * n8n Forge stream.
 * Worker calls n8n webhook (JSON response), wraps as Anthropic-compat SSE.
 * UI parser: identical to forgeStream (Anthropic format).
 * Worker endpoint: POST /ai/forge/n8n
 */
export function forgeStreamN8n(
  messages: ForgeMessage[],
  mode: ForgeMode,
  callbacks: ForgeStreamCallbacks,
): AbortController {
  // Worker wraps n8n JSON as Anthropic-compat SSE — same parser works
  return forgeStream(messages, mode, 'claude-sonnet-4-6', callbacks, '/ai/forge/n8n');
}
