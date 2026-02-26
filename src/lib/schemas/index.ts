/**
 * src/lib/schemas/index.ts
 * Zod runtime validation for ALL API responses consumed by the UI.
 * I4: every API response must be validated before use.
 */
import { z } from 'zod';

// ── Healthz ────────────────────────────────────────────────────────────────
export const HealthzSchema = z.object({
  ok: z.boolean(),
  version: z.string().optional(),
  kv: z.string().optional(),
});
export type Healthz = z.infer<typeof HealthzSchema>;

// ── VR (Verification Report) ───────────────────────────────────────────────
export const GateResultSchema = z.object({
  gate: z.string(),
  status: z.enum(['PASS', 'FAIL', 'SKIP', 'UNKNOWN']),
  message: z.string().optional(),
  evidence: z.string().optional(),
});
export type GateResult = z.infer<typeof GateResultSchema>;

export const VRDataSchema = z.object({
  schema_version: z.string().optional(),
  work_id: z.string().optional(),
  timestamp: z.string().optional(),
  anchor: z.string().optional(),
  phase: z.string().optional(),
  status: z.enum(['PASS', 'FAIL', 'PARTIAL', 'UNKNOWN']).optional(),
  gates: z.array(GateResultSchema).optional().default([]),
  signals: z.record(z.unknown()).optional(),
  metadata: z.record(z.unknown()).optional(),
}).passthrough();
export type VRData = z.infer<typeof VRDataSchema>;

// ── Evidence entry ─────────────────────────────────────────────────────────
export const EvidenceEntrySchema = z.object({
  id: z.string().optional(),
  type: z.string().optional(),
  sha: z.string().optional(),
  path: z.string().optional(),
  status: z.enum(['PASS', 'FAIL', 'UNKNOWN']).optional(),
  timestamp: z.string().optional(),
  message: z.string().optional(),
  url: z.string().optional(),
}).passthrough();
export type EvidenceEntry = z.infer<typeof EvidenceEntrySchema>;

// ── Contract JSON ──────────────────────────────────────────────────────────
export const ContractSchema = z.object({
  schema_version: z.string().optional(),
  anchor: z.string().optional(),
  gates: z.array(z.string()).optional(),
  invariants: z.array(z.string()).optional(),
}).passthrough();
export type Contract = z.infer<typeof ContractSchema>;

// ── GitHub Actions run ─────────────────────────────────────────────────────
export const WorkflowRunSchema = z.object({
  id: z.number(),
  name: z.string(),
  status: z.string().nullable(),
  conclusion: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  html_url: z.string(),
  run_number: z.number().optional(),
  event: z.string().optional(),
}).passthrough();

export const WorkflowRunsResponseSchema = z.object({
  total_count: z.number(),
  workflow_runs: z.array(WorkflowRunSchema),
});
export type WorkflowRun = z.infer<typeof WorkflowRunSchema>;

// ── PR ─────────────────────────────────────────────────────────────────────
export const PRSchema = z.object({
  id: z.number(),
  number: z.number(),
  title: z.string(),
  state: z.enum(['open', 'closed']),
  html_url: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  user: z.object({ login: z.string() }).optional(),
  head: z.object({ ref: z.string(), sha: z.string() }).optional(),
}).passthrough();

export const PRsResponseSchema = z.array(PRSchema);
export type PR = z.infer<typeof PRSchema>;

// ── Arsenal item ───────────────────────────────────────────────────────────
export const ArsenalItemSchema = z.object({
  id: z.string(),
  title: z.string().optional(),
  role: z.string().optional(),
  target: z.string().optional(),
  content: z.string().optional(),
  tags: z.array(z.string()).optional().default([]),
  category: z.string().optional(),
}).passthrough();
export type ArsenalItem = z.infer<typeof ArsenalItemSchema>;

// ── Error taxonomy ─────────────────────────────────────────────────────────
export const AXLErrorCodeSchema = z.enum([
  'UNAUTHORIZED',
  'RATE_LIMITED',
  'NOT_FOUND',
  'SERVER_ERROR',
  'NETWORK_ERROR',
  'VALIDATION_ERROR',
  'BFF_UNAVAILABLE',
  'UNKNOWN',
]);
export type AXLErrorCode = z.infer<typeof AXLErrorCodeSchema>;

export class AXLApiError extends Error {
  constructor(
    public readonly code: AXLErrorCode,
    message: string,
    public readonly status?: number,
    public readonly retryAfter?: number,
  ) {
    super(message);
    this.name = 'AXLApiError';
  }

  static fromResponse(status: number, body: string): AXLApiError {
    if (status === 401 || status === 403) return new AXLApiError('UNAUTHORIZED', 'Authentication required', status);
    if (status === 429) {
      const ra = parseInt(body.match(/"retry_after":(\d+)/)?.[1] ?? '60', 10);
      return new AXLApiError('RATE_LIMITED', 'Rate limited — retry later', status, ra);
    }
    if (status === 404) return new AXLApiError('NOT_FOUND', 'Resource not found', status);
    if (status >= 500) return new AXLApiError('SERVER_ERROR', `Server error ${status}`, status);
    return new AXLApiError('UNKNOWN', `HTTP ${status}: ${body.slice(0, 200)}`, status);
  }
}

/** Parse + validate API response. Throws AXLApiError on validation failure. */
export async function parseResponse<T>(
  res: Response,
  schema: z.ZodSchema<T>,
): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw AXLApiError.fromResponse(res.status, text);
  }
  const json = await res.json();
  const result = schema.safeParse(json);
  if (!result.success) {
    throw new AXLApiError(
      'VALIDATION_ERROR',
      `Schema validation failed: ${result.error.message}`,
    );
  }
  return result.data;
}
