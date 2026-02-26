import { describe, expect, it } from "vitest";
import { formatDiagnostic, isAuthError, isAuthLikeError, isAxlError, isRateLimitError, isRateLimitLikeError } from "@/lib/error";

describe("error helpers", () => {
  it("detects AxlError variants", () => {
    const auth = { kind: "AuthError", message: "denied", method: "GET", requestId: "r1", status: 401, url: "/x" };
    expect(isAxlError(auth)).toBe(true);
    expect(isAuthError(auth)).toBe(true);

    const rate = { kind: "RateLimitError", message: "slow", method: "GET", requestId: "r2", status: 429, url: "/x", retryAfterSec: 1 };
    expect(isRateLimitError(rate)).toBe(true);
  });

  it("supports legacy-like guard checks", () => {
    expect(isAuthLikeError({ code: "UNAUTHORIZED" })).toBe(true);
    expect(isRateLimitLikeError({ status: 429 })).toBe(true);
    expect(isAuthLikeError({ message: "x" })).toBe(false);
  });

  it("formats diagnostics", () => {
    const output = formatDiagnostic({ kind: "HttpError", message: "bad", method: "POST", requestId: "r3", status: 500, url: "/x", code: "E" });
    expect(output).toMatchObject({ kind: "HttpError", requestId: "r3", status: 500, code: "E" });
    expect(typeof output.timestamp).toBe("string");
  });
});
