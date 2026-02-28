import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AXLApiError } from '@/lib/api';

describe('dispatchRunEngine auth header', () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.stubEnv('VITE_AXL_API_BASE', 'http://localhost:8787');
    vi.stubEnv('VITE_AXL_API_KEY', 'test-key');
    // @ts-expect-error partial response
    fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true, dispatched: 'run-engine', ts: '2026-01-01T00:00:00Z' }),
    });
  });

  afterEach(() => {
    fetchSpy.mockRestore();
    vi.unstubAllEnvs();
  });

  it('sends X-AXL-Api-Key for /dispatch/run-engine', async () => {
    const { dispatchRunEngine } = await import('@/lib/api');
    await dispatchRunEngine({ source: 'test' });

    const [, init] = fetchSpy.mock.calls[0] ?? [];
    const headers = new Headers((init as RequestInit).headers);
    expect(headers.get('X-AXL-Api-Key')).toBe('test-key');
  });

  it('does not retry POST /dispatch/run-engine on transient server errors', async () => {
    fetchSpy.mockResolvedValueOnce({
      ok: false,
      status: 503,
      headers: new Headers({ 'Retry-After': '1' }),
      json: async () => ({ error: 'SERVER_ERROR', detail: 'temporary outage' }),
    } as Response);

    const { dispatchRunEngine } = await import('@/lib/api');

    await expect(dispatchRunEngine({ source: 'test' })).rejects.toMatchObject<Partial<AXLApiError>>({
      code: 'SERVER_ERROR',
      status: 503,
    });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });
});
