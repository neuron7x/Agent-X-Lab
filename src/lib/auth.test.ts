import { afterEach, describe, expect, it, vi } from "vitest";
import { __resetAuthForTests, getAuthSnapshot, initializeAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/apiFetch";
import { __resetAuthEventsForTests } from "@/lib/authEvents";

const originalFetch = global.fetch;
const originalCrypto = global.crypto;
const originalEnv = import.meta.env;

afterEach(() => {
  global.fetch = originalFetch;
  global.crypto = originalCrypto;
  __resetAuthForTests();
  __resetAuthEventsForTests();
  Object.defineProperty(import.meta, "env", { configurable: true, value: originalEnv });
  vi.restoreAllMocks();
});

const setUuid = (value: string): void => {
  Object.defineProperty(global, "crypto", {
    value: { randomUUID: vi.fn(() => value) },
    configurable: true,
  });
};

const setEnv = (): void => {
  Object.defineProperty(import.meta, "env", { configurable: true, value: { DEV: true } });
};

describe("auth state transitions", () => {
  it("sets AUTHORIZED when whoami returns user", async () => {
    setEnv();
    setUuid("req-auth");
    global.fetch = vi.fn(async () => new Response(JSON.stringify({ ok: true, user: { email: "test@example.com" } }), { status: 200, headers: { "content-type": "application/json" } })) as typeof fetch;

    await initializeAuth();

    expect(getAuthSnapshot()).toEqual({ status: "AUTHORIZED", user: { email: "test@example.com" } });
  });

  it("sets UNAUTHORIZED with whoami_missing on 404", async () => {
    setEnv();
    setUuid("req-auth");
    global.fetch = vi.fn(async () => new Response("missing", { status: 404 })) as typeof fetch;

    await initializeAuth();

    expect(getAuthSnapshot()).toEqual({ status: "UNAUTHORIZED", reason: "whoami_missing" });
  });

  it("sets UNAUTHORIZED when auth failure event is emitted from apiFetch", async () => {
    setEnv();
    setUuid("req-auth");
    global.fetch = vi.fn(async () => new Response(JSON.stringify({ ok: true, user: { email: "user@example.com" } }), { status: 200, headers: { "content-type": "application/json" } })) as typeof fetch;
    await initializeAuth();

    global.fetch = vi.fn(async () => new Response("forbidden", { status: 403 })) as typeof fetch;
    await expect(apiFetch({ url: "/protected" })).rejects.toMatchObject({ kind: "AuthError", status: 403 });

    expect(getAuthSnapshot()).toEqual({ status: "UNAUTHORIZED", reason: "Authentication required (403)" });
  });
});
