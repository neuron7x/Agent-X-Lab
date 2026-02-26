import { useState } from 'react';
import type { EvidenceEntry, PullRequest } from '@/lib/types';
import type { TranslationKey } from '@/lib/i18n';
import { useLanguage } from '@/hooks/useLanguage';

interface EvidenceScreenProps {
  entries: EvidenceEntry[];
  prs: PullRequest[];
  parseFailures?: number;
}

function statusColor(status: string) {
  if (status === 'PASS') return 'var(--text-primary)';
  if (status === 'FAIL' || status === 'ASSUMED') return 'var(--signal-fail)';
  if (status === 'RUNNING') return 'var(--signal-running)';
  return 'var(--text-tertiary)';
}

const STATUS_I18N: Record<string, TranslationKey> = {
  PASS: 'statusPass',
  FAIL: 'statusFail',
  ASSUMED: 'statusAssumed',
  RUNNING: 'statusRunning',
  PENDING: 'statusPending',
  BLOCKED: 'statusBlocked',
};

export function EvidenceScreen({ entries, prs, parseFailures }: EvidenceScreenProps) {
  const { t } = useLanguage();
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [showPRs, setShowPRs] = useState(false);

  return (
    <div className="flex flex-col" style={{ minHeight: 'calc(100vh - 48px)', padding: 'var(--space-xl)' }}>
      <div className="flex items-center gap-3" style={{ marginBottom: 'var(--space-lg)' }}>
        <h2 style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400 }}>{t('evidence')}</h2>
        {parseFailures != null && parseFailures > 0 && (
          <span style={{ fontSize: 12, color: 'var(--signal-warn)', fontWeight: 500 }}>⚠ PARSE ({parseFailures})</span>
        )}
      </div>

      {entries.length === 0 ? (
        <div className="flex items-center justify-center h-32">
          <span style={{ fontSize: 14, color: 'var(--text-tertiary)', fontWeight: 400 }}>{t('noData')}</span>
        </div>
      ) : (
        <div className="flex flex-col">
          {entries.map((entry, i) => {
            const color = statusColor(entry.status);
            const isSelected = selectedIdx === i;
            return (
              <div key={i} onClick={() => setSelectedIdx(isSelected ? null : i)} className="cursor-pointer" style={{ borderBottom: '1px solid var(--border-default)', padding: 'var(--space-md) 0', transition: 'background 200ms ease-out' }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-tertiary)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <span style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400 }}>{entry.timestamp}</span>
                    <span style={{ fontSize: 14, color: 'var(--text-secondary)', fontWeight: 400 }}>{entry.type}</span>
                  </div>
                  <span style={{ fontSize: 12, color, fontWeight: 500 }}>{STATUS_I18N[entry.status] ? t(STATUS_I18N[entry.status]) : entry.status}</span>
                </div>
                {isSelected && (
                  <div style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginTop: 'var(--space-sm)' }}>
                    {entry.sha?.slice(0, 8)}
                    {entry.path && <span style={{ marginLeft: 8 }}>{entry.path}</span>}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div style={{ marginTop: 'var(--space-xl)' }}>
        <button
          onClick={() => setShowPRs(!showPRs)}
          className="w-full flex items-center justify-between"
          style={{ fontSize: 12, color: 'var(--text-tertiary)', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 400, borderTop: '1px solid var(--border-default)', padding: 'var(--space-md) 0' }}
        >
          <span>{t('pullRequests')} ({prs.length})</span>
          <span style={{ transition: 'transform 200ms ease-out', transform: showPRs ? 'rotate(180deg)' : 'rotate(0deg)' }}>▾</span>
        </button>
        {showPRs && prs.map((pr) => (
          <a key={pr.number} href={pr.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3" style={{ borderBottom: '1px solid var(--border-default)', textDecoration: 'none', fontSize: 14, padding: 'var(--space-md) 0', transition: 'background 200ms ease-out' }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = 'var(--bg-tertiary)'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
          >
            <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>#{pr.number}</span>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>{pr.checksPassed}/{pr.checksTotal}</span>
            <span className="truncate" style={{ color: 'var(--text-primary)', fontWeight: 400 }}>{pr.title}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
