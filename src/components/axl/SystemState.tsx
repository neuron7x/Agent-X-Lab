import type { VRData } from '@/lib/types';
import { StatusPill } from './StatusPill';
import { useLanguage } from '@/hooks/useLanguage';

interface SystemStateProps {
  data: VRData | null;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="axl-label">{label}</span>
      <span className="axl-value">{children}</span>
    </div>
  );
}

export function SystemState({ data }: SystemStateProps) {
  const { t } = useLanguage();

  if (!data) {
    return (
      <div className="axl-panel p-4 h-full" style={{ animation: 'stagger-reveal 0.3s ease-out forwards', animationDelay: '0ms' }}>
        <h2 className="axl-label mb-4" style={{ fontSize: '12px' }}>{t('systemState')}</h2>
        <div className="flex items-center justify-center h-32">
          <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{t('noData')}</span>
        </div>
      </div>
    );
  }

  const isRunning = data.status === 'RUN';
  const hasBlockers = data.blockers.length > 0;
  const isDeterminismAssumed = data.metrics.determinism === 'ASSUMED_SINGLE_RUN';

  return (
    <div className="axl-panel p-4 h-full" style={{ animation: 'stagger-reveal 0.3s ease-out forwards', animationDelay: '0ms' }}>
      <h2 className="axl-label mb-4" style={{ fontSize: '12px' }}>{t('systemState')}</h2>

      <Row label={t('vrStatus')}>
        <span
          className="font-mono font-bold"
          style={{
            fontSize: '16px',
            color: isRunning ? 'var(--signal-pass)' : 'var(--signal-warn)',
            animation: isRunning ? 'breathing-pass 2s ease-in-out infinite' : undefined,
          }}
          aria-label={`${t('vrStatus')}: ${data.status}`}
        >
          ● {data.status}
        </span>
      </Row>

      <Row label={t('workId')}>
        <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
          {data.work_id}
        </span>
      </Row>

      <Row label={t('utc')}>
        <span className="font-mono" style={{ fontSize: '11px' }}>{data.utc}</span>
      </Row>

      <Row label={t('passRate')}>
        <span className="font-mono font-medium" style={{ color: (data.metrics.pass_rate ?? 0) === 1 ? 'var(--signal-pass)' : 'var(--signal-warn)' }}>
          {((data.metrics.pass_rate ?? 0) * 100).toFixed(1)}%
        </span>
      </Row>

      <Row label={t('blockers')}>
        <span
          className="font-mono font-medium"
          style={{ color: hasBlockers ? 'var(--signal-fail)' : 'var(--signal-pass)' }}
          aria-label={`${t('blockers')}: ${data.blockers.length}`}
        >
          {data.blockers.length}
        </span>
      </Row>

      <Row label={t('determinism')}>
        <span
          className="font-mono font-medium flex items-center gap-1"
          style={{ color: isDeterminismAssumed ? 'var(--signal-assumed)' : 'var(--signal-pass)' }}
          aria-label={`${t('determinism')}: ${data.metrics.determinism}`}
        >
          {isDeterminismAssumed && <span>⚠</span>}
          {isDeterminismAssumed ? t('assumed') : data.metrics.determinism}
        </span>
      </Row>

      <div className="axl-divider" />

      <h3 className="axl-label mb-3" style={{ fontSize: '11px' }}>{t('metrics')}</h3>

      <Row label={t('baselinePass')}>
        <StatusPill status={data.metrics.baseline_pass ? 'PASS' : 'FAIL'} compact />
      </Row>

      <Row label={t('catalogOk')}>
        <StatusPill status={data.metrics.catalog_ok ? 'PASS' : 'FAIL'} compact />
      </Row>

      <Row label={t('evidenceEntries')}>
        <span className="font-mono" style={{ fontSize: '12px' }}>{data.metrics.evidence_manifest_entries}</span>
      </Row>
    </div>
  );
}
