/**
 * src/lib/api.forge.test.ts
 * GATE-CRIT-1 evidence: verifies forgeStream uses correct endpoint.
 * GATE-3 evidence: Zod schema parsing + error codes.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AXLApiError, parseResponse, VRDataSchema } from '@/lib/schemas';

// ── Helper: create a minimal SSE stream ───────────────────────────────────
function sseStream(events: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(`data: ${event}\n\n`));
      }
      controller.close();
    },
  });
}

// ── GATE-CRIT-1: endpoint routing ─────────────────────────────────────────
describe('forgeStream endpoint routing', () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // @ts-expect-error - partial mock
    fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      body: sseStream([JSON.stringify({ type: 'message_stop' })]),
    });
  });

  afterEach(() => { fetchSpy.mockRestore(); });

  it('forgeStream calls /ai/forge by default', async () => {
    // Dynamic import to get the real function
    const { forgeStream } = await import('@/lib/api');
    const ctrl = forgeStream(
      [{ role: 'user', content: 'test' }],
      'single',
      'claude-sonnet-4-6',
      { onToken: vi.fn(), onDone: vi.fn(), onError: vi.fn() },
    );
    // Wait a tick for the async fetch
    await new Promise(r => setTimeout(r, 10));
    const url = (fetchSpy.mock.calls[0]?.[0] as string) ?? '';
    expect(url).toContain('/ai/forge');
    expect(url).not.toContain('/ai/forge/gpt');
    expect(url).not.toContain('/ai/forge/n8n');
    ctrl.abort();
  });

  it('forgeStream accepts custom endpoint override → /ai/forge/n8n', async () => {
    const { forgeStream } = await import('@/lib/api');
    const ctrl = forgeStream(
      [{ role: 'user', content: 'test' }],
      'single',
      'claude-sonnet-4-6',
      { onToken: vi.fn(), onDone: vi.fn(), onError: vi.fn() },
      '/ai/forge/n8n',
    );
    await new Promise(r => setTimeout(r, 10));
    const url = (fetchSpy.mock.calls[0]?.[0] as string) ?? '';
    expect(url).toContain('/ai/forge/n8n');
    ctrl.abort();
  });

  it('forgeStreamGPT calls /ai/forge/gpt', async () => {
    const { forgeStreamGPT } = await import('@/lib/api');
    const ctrl = forgeStreamGPT(
      [{ role: 'user', content: 'test' }],
      'single',
      { onToken: vi.fn(), onDone: vi.fn(), onError: vi.fn() },
    );
    await new Promise(r => setTimeout(r, 10));
    const url = (fetchSpy.mock.calls[0]?.[0] as string) ?? '';
    expect(url).toContain('/ai/forge/gpt');
    ctrl.abort();
  });

  it('forgeStreamN8n routes to /ai/forge/n8n', async () => {
    const { forgeStreamN8n } = await import('@/lib/api');
    const ctrl = forgeStreamN8n(
      [{ role: 'user', content: 'test' }],
      'single',
      { onToken: vi.fn(), onDone: vi.fn(), onError: vi.fn() },
    );
    await new Promise(r => setTimeout(r, 10));
    const url = (fetchSpy.mock.calls[0]?.[0] as string) ?? '';
    expect(url).toContain('/ai/forge/n8n');
    ctrl.abort();
  });
});

// ── GATE-3: Zod schema validation ─────────────────────────────────────────
describe('parseResponse + Zod schemas', () => {
  it('parses valid VRData', async () => {
    const data = {
      work_id: 'abc123',
      timestamp: '2026-01-01T00:00:00Z',
      status: 'PASS',
      gates: [{ gate: 'TEST', status: 'PASS' }],
    };
    const res = new Response(JSON.stringify(data), { status: 200 });
    const result = await parseResponse(res, VRDataSchema);
    expect(result.status).toBe('PASS');
    expect(result.gates).toHaveLength(1);
  });

  it('throws AXLApiError on HTTP 401', async () => {
    const res = new Response('{}', { status: 401 });
    await expect(parseResponse(res, VRDataSchema)).rejects.toThrow(AXLApiError);
    await expect(parseResponse(new Response('{}', { status: 401 }), VRDataSchema))
      .rejects.toMatchObject({ code: 'UNAUTHORIZED' });
  });

  it('throws AXLApiError on HTTP 429 with retryAfter', async () => {
    const res = new Response(JSON.stringify({ retry_after: 30 }), { status: 429 });
    try {
      await parseResponse(res, VRDataSchema);
      throw new Error('Expected throw');
    } catch (e) {
      expect(e).toBeInstanceOf(AXLApiError);
      expect((e as AXLApiError).code).toBe('RATE_LIMITED');
      expect((e as AXLApiError).retryAfter).toBe(30);
    }
  });

  it('throws VALIDATION_ERROR on schema mismatch', async () => {
    const invalid = { status: 'NOT_A_VALID_STATUS_XYZ' };
    const res = new Response(JSON.stringify(invalid), { status: 200 });
    await expect(parseResponse(res, VRDataSchema)).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
    });
  });

  it('passthrough fields preserved', async () => {
    const data = { status: 'PASS', extra_field: 'preserved' };
    const res = new Response(JSON.stringify(data), { status: 200 });
    const result = await parseResponse(res, VRDataSchema);
    expect((result as Record<string, unknown>).extra_field).toBe('preserved');
  });
});

// ── GATE-3: AXLApiError taxonomy ──────────────────────────────────────────
describe('AXLApiError.fromResponse', () => {
  it.each([
    [401, 'UNAUTHORIZED'],
    [403, 'UNAUTHORIZED'],
    [404, 'NOT_FOUND'],
    [500, 'SERVER_ERROR'],
    [503, 'SERVER_ERROR'],
  ])('status %d → code %s', (status, code) => {
    const err = AXLApiError.fromResponse(status, '');
    expect(err.code).toBe(code);
    expect(err.status).toBe(status);
  });
});
