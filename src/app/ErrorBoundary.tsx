import React from "react";
import { getLastRequestId } from "@/lib/apiFetch";
import { formatDiagnostic, isAxlError } from "@/lib/error";

type ErrorBoundaryState = {
  hasError: boolean;
  capturedError?: unknown;
  errorMessage?: string;
  stack?: string;
  timestamp?: string;
};

export class ErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      capturedError: error,
      hasError: true,
      errorMessage: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
    };
  }

  componentDidCatch(error: Error): void {
    this.setState({ capturedError: error, stack: error.stack });
  }

  private resetBoundary = (): void => {
    this.setState({ hasError: false, capturedError: undefined, errorMessage: undefined, stack: undefined, timestamp: undefined });
  };

  private copyDiagnostics = async (): Promise<void> => {
    const captured = this.state.capturedError;
    const payload = {
      error: isAxlError(captured)
        ? formatDiagnostic(captured)
        : {
            message: this.state.errorMessage,
            stack: this.state.stack,
          },
      lastRequestId: getLastRequestId(),
      location: window.location.href,
      timestamp: this.state.timestamp ?? new Date().toISOString(),
      userAgent: navigator.userAgent,
    };
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
  };

  render(): React.ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <h1 className="text-2xl font-semibold">Something went wrong</h1>
        <p className="max-w-lg text-sm text-muted-foreground">An unexpected UI error occurred.</p>
        <div className="flex flex-wrap justify-center gap-2">
          <button className="rounded border px-3 py-2" onClick={this.resetBoundary}>
            Retry
          </button>
          <button className="rounded border px-3 py-2" onClick={() => window.location.reload()}>
            Reload page
          </button>
          <button className="rounded border px-3 py-2" onClick={() => void this.copyDiagnostics()}>
            Copy Diagnostic Data
          </button>
        </div>
      </div>
    );
  }
}
