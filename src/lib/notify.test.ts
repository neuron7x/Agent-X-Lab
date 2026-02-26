import { describe, expect, it, vi } from "vitest";

const toastMock = Object.assign(vi.fn(), { error: vi.fn() });
vi.mock("sonner", () => ({ toast: toastMock }));

import { notify } from "@/lib/notify";

describe("notify", () => {
  it("sends error toast", () => {
    notify({ kind: "error", title: "oops", detail: "detail", requestId: "req-1" });
    expect(toastMock.error).toHaveBeenCalledWith("oops", { description: "detail\nrequest: req-1" });
  });

  it("sends info toast", () => {
    notify({ kind: "info", title: "ok" });
    expect(toastMock).toHaveBeenCalledWith("ok", { description: "" });
  });
});
