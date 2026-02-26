import { z, type ZodType } from "zod";
import type { AxlError } from "@/lib/error";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD" | "OPTIONS";

type ApiFetchBaseOptions = {
  url: string;
  method?: HttpMethod;
  headers?: HeadersInit;
  body?: BodyInit | null;
  signal?: AbortSignal;
  timeoutMs?: number;
  idempotencyKey?: string;
};

type ApiFetchSchemaOptions<T extends ZodType> = ApiFetchBaseOptions & {
  schema: T;
};

type ApiFetchNoSchemaOptions = ApiFetchBaseOptions & {
  schema?: undefined;
};

let lastRequestId: string | null = null;

const IDEMPOTENT_METHODS = new Set<HttpMethod>(["POST", "PUT", "PATCH"]);

const defaultTimeout = (method: HttpMethod): number => (method === "GET" ? 15000 : 30000);

const truncBodyText = (text: string): string => text.slice(0, 8192);

const parseRetryAfter = (header: string | null): number | undefined => {
  if (!header) return undefined;
  const asNumber = Number.parseInt(header, 10);
  if (!Number.isNaN(asNumber)) return asNumber;
  const ts = Date.parse(header);
  if (Number.isNaN(ts)) return undefined;
  const deltaMs = ts - Date.now();
  return deltaMs > 0 ? Math.ceil(deltaMs / 1000) : 0;
};

const toAxlError = (
  response: Response,
  requestId: string,
  url: string,
  method: HttpMethod,
  bodyText: string,
): AxlError => {
  if (response.status === 401 || response.status === 403) {
    return {
      kind: "AuthError",
      message: `Authentication required (${response.status})`,
      requestId,
      url,
      method,
      status: response.status,
    };
  }

  if (response.status === 429) {
    return {
      kind: "RateLimitError",
      message: "Rate limited",
      requestId,
      url,
      method,
      status: 429,
      retryAfterSec: parseRetryAfter(response.headers.get("Retry-After")),
    };
  }

  return {
    kind: "HttpError",
    message: `HTTP ${response.status}`,
    requestId,
    url,
    method,
    status: response.status,
    bodyText,
  };
};

const resolveMethod = (method?: string): HttpMethod => (method?.toUpperCase() as HttpMethod) ?? "GET";

const withTimeout = (timeoutMs: number, signal?: AbortSignal): AbortController => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort("timeout"), timeoutMs);
  if (signal) {
    signal.addEventListener("abort", () => controller.abort(signal.reason), { once: true });
  }
  controller.signal.addEventListener("abort", () => clearTimeout(timer), { once: true });
  return controller;
};

const safeGetRetryable = (method: HttpMethod, attempt: number): boolean => method === "GET" && attempt < 1;

const parseJson = async (response: Response): Promise<unknown> => {
  try {
    return (await response.json()) as unknown;
  } catch {
    return undefined;
  }
};

export const getLastRequestId = (): string | null => lastRequestId;

export async function apiFetch<T extends ZodType>(opts: ApiFetchSchemaOptions<T>): Promise<{ data: z.infer<T>; requestId: string }>;
export async function apiFetch(opts: ApiFetchNoSchemaOptions): Promise<{ data: unknown; requestId: string }>;
export async function apiFetch<T extends ZodType>(
  opts: ApiFetchSchemaOptions<T> | ApiFetchNoSchemaOptions,
): Promise<{ data: unknown; requestId: string }> {
  const method = resolveMethod(opts.method);
  const requestId = crypto.randomUUID();
  lastRequestId = requestId;
  const timeoutController = withTimeout(opts.timeoutMs ?? defaultTimeout(method), opts.signal);
  const headers = new Headers(opts.headers ?? {});
  headers.set("X-Request-Id", requestId);
  if (IDEMPOTENT_METHODS.has(method)) {
    headers.set("X-Idempotency-Key", opts.idempotencyKey ?? crypto.randomUUID());
  }

  let response: Response;
  for (let attempt = 0; ; attempt += 1) {
    try {
      response = await fetch(opts.url, {
        method,
        headers,
        body: opts.body,
        signal: timeoutController.signal,
      });
      break;
    } catch (error) {
      const networkError: AxlError = {
        kind: "NetworkError",
        message: "Network request failed",
        requestId,
        url: opts.url,
        method,
        cause: error instanceof Error ? error.message : String(error),
      };
      if (safeGetRetryable(method, attempt)) {
        continue;
      }
      throw networkError;
    }
  }

  if (response.status === 204) {
    return { data: null, requestId };
  }

  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
  const isJson = contentType.includes("application/json") || contentType.includes("+json");

  if (!response.ok) {
    const bodyText = truncBodyText(await response.text());
    throw toAxlError(response, requestId, opts.url, method, bodyText);
  }

  if (!isJson) {
    const text = truncBodyText(await response.text());
    return { data: text, requestId };
  }

  const parsed = await parseJson(response);

  if (opts.schema) {
    const validated = opts.schema.safeParse(parsed);
    if (!validated.success) {
      const schemaError: AxlError = {
        kind: "HttpError",
        message: "Schema validation failed",
        requestId,
        url: opts.url,
        method,
        status: response.status,
        code: "SCHEMA_INVALID",
        bodyText: truncBodyText(JSON.stringify(validated.error.format())),
      };
      throw schemaError;
    }
    return { data: validated.data, requestId };
  }

  return { data: parsed, requestId };
}

export async function apiFetchResponse(opts: ApiFetchBaseOptions): Promise<{ response: Response; requestId: string }> {
  const method = resolveMethod(opts.method);
  const requestId = crypto.randomUUID();
  lastRequestId = requestId;
  const timeoutController = withTimeout(opts.timeoutMs ?? defaultTimeout(method), opts.signal);
  const headers = new Headers(opts.headers ?? {});
  headers.set("X-Request-Id", requestId);
  if (IDEMPOTENT_METHODS.has(method)) {
    headers.set("X-Idempotency-Key", opts.idempotencyKey ?? crypto.randomUUID());
  }

  try {
    const response = await fetch(opts.url, {
      method,
      headers,
      body: opts.body,
      signal: timeoutController.signal,
    });
    return { response, requestId };
  } catch (error) {
    const networkError: AxlError = {
      kind: "NetworkError",
      message: "Network request failed",
      requestId,
      url: opts.url,
      method,
      cause: error instanceof Error ? error.message : String(error),
    };
    throw networkError;
  }
}
