/**
 * src/components/axl/ProtectedAction.tsx
 * Phase 5.3: ProtectedAction wrapper.
 * Dangerous actions (dispatch, forge calls) must pass auth gate.
 *
 * Rules:
 * 1. In dev (localhost) without VITE_AXL_API_KEY → warn in console, allow with banner (bypass).
 * 2. In production without VITE_AXL_API_KEY → block and show config error.
 * 3. With VITE_AXL_API_KEY set → pass through to children.
 *
 * I2: Never stores or logs the key value — only checks presence.
 * I7: No new XSS surface — children rendered as-is.
 */
import { type ReactNode } from 'react';
import { ActionGateStatus, getActionGateStatus } from '@/components/axl/actionGate';

interface ProtectedActionProps {
  children: ReactNode;
  /** Render when the action is blocked (no key in prod) */
  fallback?: ReactNode;
}

/**
 * Hook version — lets components check gate status and show inline errors.
 *
 * Usage:
 *   const { status, gateError } = useActionGate();
 *   if (status === 'BLOCKED') return <ErrorBanner message={gateError} />;
 */
export function useActionGate() {
  const status = getActionGateStatus();

  const gateError =
    status === 'BLOCKED'
      ? 'VITE_AXL_API_KEY is not configured. Dispatch and Forge actions are disabled in production without an API key. Set it in your Vercel environment variables.'
      : status === 'DEV_BYPASS'
      ? 'DEV: VITE_AXL_API_KEY not set — running with dev bypass. Set it for production.'
      : null;

  return { status, gateError, isAllowed: status !== 'BLOCKED' };
}

/**
 * Wrapper component — blocks render in production without key.
 */
export function ProtectedAction({ children, fallback }: ProtectedActionProps) {
  const { status, gateError } = useActionGate();

  if (status === 'BLOCKED') {
    return fallback != null ? (
      <>{fallback}</>
    ) : (
      <div
        role="alert"
        aria-live="assertive"
        style={{
          fontSize: 11,
          color: 'var(--signal-fail,#ff3b30)',
          padding: '8px 12px',
          border: '1px solid var(--signal-fail,#ff3b30)',
          borderRadius: 4,
          fontFamily: 'monospace',
        }}
      >
        ⛔ {gateError}
      </div>
    );
  }

  if (status === 'DEV_BYPASS') {
    // Dev warn — don't block, just surface in console
    if (typeof console !== 'undefined') {
      console.warn('[AXL ProtectedAction] DEV bypass active —', gateError);
    }
  }

  return <>{children}</>;
}
