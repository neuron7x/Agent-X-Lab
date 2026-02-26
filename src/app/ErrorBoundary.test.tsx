import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "@/app/ErrorBoundary";

vi.mock("@/lib/apiFetch", () => ({ getLastRequestId: () => "req-test" }));

const Crash = (): JSX.Element => {
  throw new Error("boom");
};

describe("ErrorBoundary", () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(async () => undefined),
      },
    });
  });

  it("renders fallback and copies diagnostics", async () => {
    render(
      <ErrorBoundary>
        <Crash />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Copy Diagnostic Data"));

    const writeText = navigator.clipboard.writeText as unknown as ReturnType<typeof vi.fn>;
    expect(writeText).toHaveBeenCalledTimes(1);
    expect(writeText.mock.calls[0][0]).toContain("req-test");
  });
});
