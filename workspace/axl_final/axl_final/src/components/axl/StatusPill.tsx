import type { GateStatus } from '@/lib/types';
import { useLanguage } from '@/hooks/useLanguage';
import type { TranslationKey } from '@/lib/i18n';

const COLORS: Record<GateStatus, string> = {
  PASS: 'var(--text-primary)',
  FAIL: 'var(--signal-fail)',
  RUNNING: 'var(--signal-running)',
  ASSUMED: 'var(--signal-fail)',
  PENDING: 'var(--text-tertiary)',
  BLOCKED: 'var(--signal-fail)',
};

const STATUS_I18N: Record<GateStatus, TranslationKey> = {
  PASS: 'statusPass',
  FAIL: 'statusFail',
  ASSUMED: 'statusAssumed',
  RUNNING: 'statusRunning',
  PENDING: 'statusPending',
  BLOCKED: 'statusBlocked',
};

export function StatusPill({ status, compact }: { status: GateStatus; compact?: boolean }) {
  const { t } = useLanguage();
  const color = COLORS[status] || 'var(--text-tertiary)';
  return (
    <span
      aria-label={`Status: ${status}`}
      className="inline-flex items-center"
      style={{
        color,
        fontSize: compact ? 12 : 14,
        fontWeight: 500,
      }}
    >
      {t(STATUS_I18N[status])}
    </span>
  );
}
