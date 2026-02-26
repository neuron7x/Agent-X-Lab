import { afterAll, describe, expect, it } from "vitest";
import { getApiBase } from "@/lib/apiBase";

const originalEnv = import.meta.env;

const setEnv = (env: Record<string, unknown>): void => {
  Object.defineProperty(import.meta, "env", { configurable: true, value: env });
};

describe("getApiBase", () => {
  it("returns configured base without trailing slash", () => {
    setEnv({ DEV: false, VITE_AXL_API_BASE: "https://api.example.com/" });
    expect(getApiBase()).toBe("https://api.example.com");
  });

  it("falls back to localhost in DEV", () => {
    setEnv({ DEV: true });
    expect(getApiBase()).toBe("http://localhost:8787");
  });

  it("throws outside DEV when missing", () => {
    setEnv({ DEV: false });
    expect(() => getApiBase()).toThrow("VITE_AXL_API_BASE is not configured");
  });
});

afterAll(() => {
  Object.defineProperty(import.meta, "env", { configurable: true, value: originalEnv });
});
