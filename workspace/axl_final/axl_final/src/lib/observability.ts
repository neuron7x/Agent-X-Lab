/**
 * src/lib/observability.ts
 * D6: Sentry error tracking + structured client logs + release tagging.
 * Loaded once at app boot (see main.tsx).
 * I2: DSN from env only — never hardcoded.
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEvent {
  level: LogLevel;
  msg: string;
  data?: Record<string, unknown>;
  ts: number;
}

/** Ring buffer of last 100 log events for debug panel. */
const LOG_RING: LogEvent[] = [];
const LOG_RING_SIZE = 100;

function pushLog(event: LogEvent) {
  LOG_RING.push(event);
  if (LOG_RING.length > LOG_RING_SIZE) LOG_RING.shift();
}

/** Structured client logger. Respects log level hierarchy. */
export const log = {
  debug: (msg: string, data?: Record<string, unknown>) => {
    if (import.meta.env.DEV) console.debug(`[AXL] ${msg}`, data ?? '');
    pushLog({ level: 'debug', msg, data, ts: Date.now() });
  },
  info: (msg: string, data?: Record<string, unknown>) => {
    if (import.meta.env.DEV) console.info(`[AXL] ${msg}`, data ?? '');
    pushLog({ level: 'info', msg, data, ts: Date.now() });
  },
  warn: (msg: string, data?: Record<string, unknown>) => {
    console.warn(`[AXL] ${msg}`, data ?? '');
    pushLog({ level: 'warn', msg, data, ts: Date.now() });
  },
  error: (msg: string, data?: Record<string, unknown>) => {
    console.error(`[AXL] ${msg}`, data ?? '');
    pushLog({ level: 'error', msg, data, ts: Date.now() });
  },
};

/** Access ring buffer for debug panel */
export function getLogRing(): Readonly<LogEvent[]> {
  return [...LOG_RING];
}

// ── Version stamp ──────────────────────────────────────────────────────────
export const VERSION = {
  sha: import.meta.env.VITE_COMMIT_SHA ?? 'local',
  buildTime: import.meta.env.VITE_BUILD_TIME ?? 'unknown',
  release: `axl-ui@${import.meta.env.VITE_COMMIT_SHA ?? 'dev'}`,
};

// ── Route timing ───────────────────────────────────────────────────────────
const routeTimings = new Map<string, number>();

export function markRouteStart(route: string) {
  routeTimings.set(route, performance.now());
}

export function markRouteEnd(route: string) {
  const start = routeTimings.get(route);
  if (start !== undefined) {
    const elapsed = performance.now() - start;
    log.info('route:load', { route, elapsed_ms: Math.round(elapsed) });
    routeTimings.delete(route);
  }
}

// ── Sentry stub (real init when VITE_SENTRY_DSN is set) ───────────────────
let sentryEnabled = false;

export async function initObservability() {
  const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined;
  if (!dsn) {
    log.info('observability: Sentry DSN not set — error tracking disabled');
    return;
  }

  try {
    // Dynamic import so Sentry bundle only loads when DSN configured
    const Sentry = await import('@sentry/react');
    Sentry.init({
      dsn,
      release: VERSION.release,
      environment: import.meta.env.MODE,
      tracesSampleRate: 0.1,
      integrations: [
        Sentry.browserTracingIntegration(),
      ],
      beforeSend(event) {
        // Redact any potential sensitive data before sending
        if (event.request?.url) {
          event.request.url = event.request.url.replace(/\/\?.*/, '/');
        }
        return event;
      },
    });
    sentryEnabled = true;
    log.info('observability: Sentry initialized', { release: VERSION.release, env: import.meta.env.MODE });
  } catch (err) {
    log.warn('observability: Sentry init failed', { err: String(err) });
  }
}

export function captureError(err: unknown, context?: Record<string, unknown>) {
  if (err instanceof Error) {
    log.error(err.message, { ...context, stack: err.stack?.split('\n').slice(0, 5).join(' | ') });
  } else {
    log.error('Unknown error', { err: String(err), ...context });
  }
  if (!sentryEnabled) return;
  import('@sentry/react').then(Sentry => {
    if (context) Sentry.withScope(scope => {
      Object.entries(context).forEach(([k, v]) => scope.setExtra(k, v));
      Sentry.captureException(err);
    });
    else Sentry.captureException(err);
  }).catch(() => {});
}
