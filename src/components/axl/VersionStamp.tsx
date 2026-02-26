/**
 * src/components/axl/VersionStamp.tsx
 * Phase 8.3: Version stamp shown in footer and /health panel.
 * D6: releases traceable via commit SHA.
 * I2: reads VITE_COMMIT_SHA / VITE_BUILD_TIME (build-time injected, not secrets).
 */
import { VERSION } from '@/lib/observability';

interface VersionStampProps {
  compact?: boolean;
  className?: string;
}

export function VersionStamp({ compact = false, className }: VersionStampProps) {
  const sha = VERSION.sha === 'local' ? 'local' : VERSION.sha.slice(0, 7);
  const buildTime = VERSION.buildTime === 'unknown'
    ? null
    : new Date(VERSION.buildTime).toISOString().slice(0, 10);

  if (compact) {
    return (
      <span
        className={className}
        style={{ fontSize: 11, color: 'var(--text-tertiary,#555)', fontFamily: 'monospace' }}
        title={`Release: ${VERSION.release} | Build: ${VERSION.buildTime}`}
      >
        {sha}
      </span>
    );
  }

  return (
    <div
      className={className}
      style={{ fontSize: 11, color: 'var(--text-tertiary,#555)', fontFamily: 'monospace', display: 'flex', gap: 8 }}
    >
      <span>v:{sha}</span>
      {buildTime && <span>built:{buildTime}</span>}
      <span style={{ color: 'var(--text-dim,#333)' }}>axl-ui</span>
    </div>
  );
}
