import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { apiFetch, apiFetchResponse } from "@/lib/apiFetch";
import { __resetAuthEventsForTests, onAuthFailure } from "@/lib/authEvents";
import { isAuthError, isRateLimitError } from "@/lib/error";

const originalFetch = global.fetch;
const originalCrypto = global.crypto;
const originalEnv = import.meta.env;

afterEach(() => {
  global.fetch = originalFetch;
  global.crypto = originalCrypto;
  __resetAuthEventsForTests();
  vi.restoreAllMocks();
  Object.defineProperty(import.meta, "env", { value: originalEnv });
});

const mockUuid = (...values: string[]): void => {
  const queue = [...values];
  Object.defineProperty(global, "crypto", {
    configurable: true,
    value: { randomUUID: vi.fn(() => queue.shift() ?? "req-fallback") },
  });
};

const setEnv = (env: Record<string, unknown>): void => {
  Object.defineProperty(import.meta, "env", { value: env, configurable: true });
};

describe("apiFetch", () => {
  it("maps 401 to AuthError and emits auth failure", async () => {
    setEnv({ DEV: true });
    mockUuid("req-1");
    global.fetch = vi.fn(async () => new Response("denied", { status: 401 })) as typeof fetch;
    const listener = vi.fn();
    onAuthFailure(listener);

    await expect(apiFetch({ url: "/x" })).rejects.toSatisfy((error: unknown) => isAuthError(error) && error.status === 401);
    expect(listener).toHaveBeenCalledWith({ reason: "Authentication required (401)", requestId: "req-1", status: 401 });
  });

  it("maps 429 to RateLimitError + retryAfterSec", async () => {
    setEnv({ DEV: true });
    mockUuid("req-2");
    global.fetch = vi.fn(async () => new Response("slow down", { status: 429, headers: { "Retry-After": "15" } })) as typeof fetch;

    await expect(apiFetch({ url: "/x" })).rejects.toSatisfy((error: unknown) => isRateLimitError(error) && error.retryAfterSec === 15);
  });

  it("maps schema mismatch to HttpError code SCHEMA_INVALID", async () => {
    setEnv({ DEV: true });
    mockUuid("req-3");
    global.fetch = vi.fn(async () => new Response(JSON.stringify({ ok: "wrong" }), { status: 200, headers: { "content-type": "application/json" } })) as typeof fetch;

    await expect(apiFetch({ url: "/x", schema: z.object({ ok: z.boolean() }) })).rejects.toMatchObject({ kind: "HttpError", code: "SCHEMA_INVALID" });
  });

  it("prefixes relative URLs with API base", async () => {
    setEnv({ DEV: false, VITE_AXL_API_BASE: "https://api.example.com" });
    mockUuid("req-4");
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } }));
    global.fetch = fetchMock as typeof fetch;

    await apiFetch({ url: "/whoami", schema: z.object({ ok: z.boolean() }) });

    expect(fetchMock).toHaveBeenCalled();
    expect(fetchMock.mock.calls[0]?.[0]).toBe("https://api.example.com/whoami");
  });

  it("apiFetchResponse sets request headers including idempotency", async () => {
    setEnv({ DEV: true });
    mockUuid("req-5", "idem-5");
    const fetchMock = vi.fn(async () => new Response("ok", { status: 200 }));
    global.fetch = fetchMock as typeof fetch;

    await apiFetchResponse({ url: "/dispatch", method: "POST" });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(headers.get("X-Request-Id")).toBe("req-5");
    expect(headers.get("X-Idempotency-Key")).toBe("idem-5");
  });
});
