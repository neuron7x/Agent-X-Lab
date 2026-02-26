import { useLanguage } from '@/hooks/useLanguage';
import type { TranslationKey } from '@/lib/i18n';
import type { Gate, VRData } from '@/lib/types';

interface BottomBarProps {
  gates: Gate[];
  vrData: VRData | null;
  iteration: number;
  sha: string;
  utc: string;
}

const CYCLE_KEYS: TranslationKey[] = ['cycleObserve', 'cycleSpecify', 'cycleExecute', 'cycleProve'];

function derivePhase(gates: Gate[], vrData: VRData | null): number {
  if (gates.length === 0) return 0;
  const hasRunning = gates.some(g => g.status === 'RUNNING');
  const hasPending = gates.some(g => g.status === 'PENDING');
  const allResolved = !hasRunning && !hasPending;

  if (hasPending && !hasRunning) return 0;
  if (hasRunning) return 1;
  if (allResolved) {
    if (vrData?.status === 'RUN' && (!Array.isArray(vrData.blockers) || vrData.blockers.length === 0)) {
      return 3;
    }
    return 2;
  }
  return 0;
}

export function BottomBar({ gates, vrData, iteration, sha, utc }: BottomBarProps) {
  const { t } = useLanguage();
  const activePhase = derivePhase(gates, vrData);

  return (
    <footer
      className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-between"
      style={{ height: 40, background: 'var(--bg-primary)', borderTop: '1px solid var(--border-default)', padding: '0 var(--space-lg)' }}
    >
      <div className="flex items-center gap-2">
        {CYCLE_KEYS.map((key, i) => {
          const isActive = i === activePhase;
          return (
            <span
              key={key}
              style={{
                fontSize: 12, padding: '2px 10px', borderRadius: 999,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? 'var(--text-primary)' : 'var(--text-tertiary)',
                background: isActive ? 'var(--bg-tertiary)' : 'transparent',
                transition: 'all 200ms ease-out',
              }}
            >
              {t(key)}
            </span>
          );
        })}
      </div>

      <div className="flex items-center gap-6">
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>N={iteration} {t('iter')}</span>
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>SHA: {sha.slice(0, 8)}</span>
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{utc}</span>
      </div>
    </footer>
  );
}
