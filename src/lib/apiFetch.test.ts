import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { apiFetch } from "@/lib/apiFetch";
import { isAuthError, isRateLimitError } from "@/lib/error";

const originalFetch = global.fetch;
const originalCrypto = global.crypto;

afterEach(() => {
  global.fetch = originalFetch;
  global.crypto = originalCrypto;
  vi.restoreAllMocks();
});

const mockUuid = (...values: string[]): void => {
  const queue = [...values];
  Object.defineProperty(global, "crypto", {
    value: {
      randomUUID: vi.fn(() => queue.shift() ?? "req-fallback"),
    },
    configurable: true,
  });
};

describe("apiFetch", () => {
  it("maps 401 to AuthError", async () => {
    mockUuid("req-1");
    global.fetch = vi.fn(async () => new Response("denied", { status: 401 })) as typeof fetch;

    await expect(apiFetch({ url: "/x" })).rejects.toSatisfy((error: unknown) => isAuthError(error) && error.status === 401);
  });

  it("maps 429 to RateLimitError + retryAfterSec", async () => {
    mockUuid("req-2");
    global.fetch = vi.fn(
      async () =>
        new Response("slow down", {
          status: 429,
          headers: { "Retry-After": "15" },
        }),
    ) as typeof fetch;

    await expect(apiFetch({ url: "/x" })).rejects.toSatisfy(
      (error: unknown) => isRateLimitError(error) && error.retryAfterSec === 15,
    );
  });

  it("maps 500 to HttpError", async () => {
    mockUuid("req-3");
    global.fetch = vi.fn(async () => new Response("boom", { status: 500 })) as typeof fetch;

    await expect(apiFetch({ url: "/x" })).rejects.toMatchObject({ kind: "HttpError", status: 500 });
  });

  it("maps schema mismatch to HttpError code SCHEMA_INVALID", async () => {
    mockUuid("req-4");
    global.fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ ok: "wrong" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
    ) as typeof fetch;

    await expect(apiFetch({ url: "/x", schema: z.object({ ok: z.boolean() }) })).rejects.toMatchObject({
      kind: "HttpError",
      code: "SCHEMA_INVALID",
    });
  });


  it("maps invalid JSON to HttpError code SCHEMA_INVALID", async () => {
    mockUuid("req-4b");
    global.fetch = vi.fn(
      async () =>
        new Response("not-json", {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
    ) as typeof fetch;

    await expect(apiFetch({ url: "/x" })).rejects.toMatchObject({
      kind: "HttpError",
      code: "SCHEMA_INVALID",
    });
  });

  it("ensures X-Request-Id always present", async () => {
    mockUuid("req-5");
    const fetchMock = vi.fn(
      async () =>
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
    );
    global.fetch = fetchMock as typeof fetch;

    await apiFetch({ url: "/x" });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(headers.get("X-Request-Id")).toBe("req-5");
  });

  it("ensures X-Idempotency-Key present for POST", async () => {
    mockUuid("req-6", "idem-6");
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } }));
    global.fetch = fetchMock as typeof fetch;

    await apiFetch({
      url: "/x",
      method: "POST",
      body: JSON.stringify({ hello: "world" }),
      headers: { "content-type": "application/json" },
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(headers.get("X-Idempotency-Key")).toBe("idem-6");
  });
});
