import { describe, expect, it, vi } from "vitest";
import { __resetAuthEventsForTests, emitAuthFailure, onAuthFailure } from "@/lib/authEvents";

describe("authEvents", () => {
  it("subscribes and emits", () => {
    const listener = vi.fn();
    const unsubscribe = onAuthFailure(listener);

    emitAuthFailure({ reason: "forbidden", requestId: "req-1", status: 403 });
    expect(listener).toHaveBeenCalledWith({ reason: "forbidden", requestId: "req-1", status: 403 });

    unsubscribe();
    emitAuthFailure({ reason: "x", requestId: "req-2", status: 401 });
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("reset clears subscribers", () => {
    const listener = vi.fn();
    onAuthFailure(listener);
    __resetAuthEventsForTests();
    emitAuthFailure({ reason: "x", requestId: "req-2", status: 401 });
    expect(listener).not.toHaveBeenCalled();
  });
});
