export type AxlError =
  | {
      kind: "NetworkError";
      message: string;
      requestId: string;
      url: string;
      method: string;
      cause?: string;
    }
  | {
      kind: "HttpError";
      message: string;
      requestId: string;
      url: string;
      method: string;
      status: number;
      code?: string;
      bodyText?: string;
    }
  | {
      kind: "AuthError";
      message: string;
      requestId: string;
      url: string;
      method: string;
      status: 401 | 403;
    }
  | {
      kind: "RateLimitError";
      message: string;
      requestId: string;
      url: string;
      method: string;
      status: 429;
      retryAfterSec?: number;
    };

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

export const isAxlError = (value: unknown): value is AxlError => {
  if (!isRecord(value) || typeof value.kind !== "string") {
    return false;
  }
  if (
    typeof value.message !== "string" ||
    typeof value.requestId !== "string" ||
    typeof value.url !== "string" ||
    typeof value.method !== "string"
  ) {
    return false;
  }

  if (value.kind === "NetworkError") {
    return value.cause === undefined || typeof value.cause === "string";
  }

  if (value.kind === "HttpError") {
    return (
      typeof value.status === "number" &&
      (value.code === undefined || typeof value.code === "string") &&
      (value.bodyText === undefined || typeof value.bodyText === "string")
    );
  }

  if (value.kind === "AuthError") {
    return value.status === 401 || value.status === 403;
  }

  if (value.kind === "RateLimitError") {
    return value.status === 429 && (value.retryAfterSec === undefined || typeof value.retryAfterSec === "number");
  }

  return false;
};

export const isAuthError = (value: unknown): value is Extract<AxlError, { kind: "AuthError" }> =>
  isAxlError(value) && value.kind === "AuthError";

export const isRateLimitError = (value: unknown): value is Extract<AxlError, { kind: "RateLimitError" }> =>
  isAxlError(value) && value.kind === "RateLimitError";

export const formatDiagnostic = (error: AxlError) => ({
  kind: error.kind,
  message: error.message,
  requestId: error.requestId,
  status: "status" in error ? error.status : undefined,
  code: "code" in error ? error.code : undefined,
  url: error.url,
  method: error.method,
  timestamp: new Date().toISOString(),
  bodyText: "bodyText" in error ? error.bodyText : undefined,
  retryAfterSec: "retryAfterSec" in error ? error.retryAfterSec : undefined,
  cause: "cause" in error ? error.cause : undefined,
});
