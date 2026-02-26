import { afterEach, describe, expect, it, vi } from "vitest";
import { __resetAuthForTests, getAuthSnapshot, initializeAuth } from "@/lib/auth";

const originalFetch = global.fetch;
const originalCrypto = global.crypto;

afterEach(() => {
  global.fetch = originalFetch;
  global.crypto = originalCrypto;
  __resetAuthForTests();
  vi.restoreAllMocks();
});

const setUuid = (): void => {
  Object.defineProperty(global, "crypto", {
    value: { randomUUID: vi.fn(() => "req-auth") },
    configurable: true,
  });
};

describe("auth state transitions", () => {
  it("sets AUTHORIZED when whoami returns user", async () => {
    setUuid();
    global.fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ ok: true, user: { email: "test@example.com" } }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
    ) as typeof fetch;

    await initializeAuth();

    expect(getAuthSnapshot()).toEqual({
      status: "AUTHORIZED",
      user: { email: "test@example.com" },
    });
  });

  it("sets UNAUTHORIZED with whoami_missing on 404", async () => {
    setUuid();
    global.fetch = vi.fn(async () => new Response("missing", { status: 404 })) as typeof fetch;

    await initializeAuth();

    expect(getAuthSnapshot()).toEqual({
      status: "UNAUTHORIZED",
      reason: "whoami_missing",
    });
  });

  it("sets UNAUTHORIZED for forbidden", async () => {
    setUuid();
    global.fetch = vi.fn(async () => new Response("forbidden", { status: 403 })) as typeof fetch;

    await initializeAuth();

    expect(getAuthSnapshot()).toEqual({
      status: "UNAUTHORIZED",
      reason: "AuthError",
    });
  });
});
