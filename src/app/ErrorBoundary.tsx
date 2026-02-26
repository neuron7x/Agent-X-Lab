import React from "react";
import { getLastRequestId } from "@/lib/apiFetch";

type ErrorBoundaryState = {
  hasError: boolean;
  errorMessage?: string;
  stack?: string;
  timestamp?: string;
};

export class ErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      errorMessage: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
    };
  }

  componentDidCatch(error: Error): void {
    this.setState({ stack: error.stack });
  }

  private copyDiagnostics = async (): Promise<void> => {
    const payload = {
      timestamp: this.state.timestamp ?? new Date().toISOString(),
      location: window.location.href,
      userAgent: navigator.userAgent,
      lastRequestId: getLastRequestId(),
      error: {
        message: this.state.errorMessage,
        stack: this.state.stack,
      },
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
          <button className="rounded border px-3 py-2" onClick={() => window.location.reload()}>
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
