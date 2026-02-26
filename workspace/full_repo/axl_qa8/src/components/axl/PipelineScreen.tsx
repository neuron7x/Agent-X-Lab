import { useState } from 'react';
import type { Gate } from '@/lib/types';
import { StatusPill } from './StatusPill';
import { ARALoop } from './ARALoop';
import { useLanguage } from '@/hooks/useLanguage';

interface PipelineScreenProps {
  gates: Gate[];
  contractError?: string | null;
}

const STATUS_ORDER: Record<string, number> = { FAIL: 0, BLOCKED: 1, ASSUMED: 2, RUNNING: 3, PENDING: 4, PASS: 5 };

function gateColor(status: string) {
  if (status === 'FAIL' || status === 'BLOCKED' || status === 'ASSUMED') return 'var(--signal-fail)';
  if (status === 'RUNNING') return 'var(--signal-running)';
  if (status === 'PENDING') return 'var(--signal-warn)';
  return 'var(--text-secondary)';
}

export function PipelineScreen({ gates, contractError }: PipelineScreenProps) {
  const { t } = useLanguage();
  const [gatesExpanded, setGatesExpanded] = useState(true);
  const [expandedGate, setExpandedGate] = useState<string | null>(null);

  const totalGates = gates.length;
  const passedGates = gates.filter(g => g.status === 'PASS').length;
  const failedGates = gates.filter(g => g.status === 'FAIL').length;
  const progressPercent = totalGates > 0 ? Math.round((passedGates / totalGates) * 100) : 0;

  const araPhase = progressPercent >= 100 ? 3 : progressPercent >= 66 ? 2 : progressPercent >= 33 ? 1 : 0;

  const sorted = [...gates].sort((a, b) => (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9));

  return (
    <div className="flex flex-col" style={{ minHeight: 'calc(100vh - 48px)', padding: 'var(--space-xl)' }}>
      {contractError && (
        <div style={{ fontSize: 12, color: 'var(--signal-fail)', border: '1px solid var(--signal-fail)', padding: '8px 16px', borderRadius: 12, fontWeight: 400, marginBottom: 'var(--space-lg)' }}>
          ⚠ {contractError}
        </div>
      )}

      <div style={{ marginBottom: 'var(--space-xl)' }}>
        <h2 className="text-center" style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginBottom: 'var(--space-xs)' }}>{t('araLoop')}</h2>
        <ARALoop activePhase={araPhase} />
      </div>

      <div style={{ marginBottom: 'var(--space-xl)' }}>
        <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-sm)' }}>
          <span style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400 }}>{t('gates')}</span>
          <span style={{ fontSize: 14, color: failedGates > 0 ? 'var(--signal-fail)' : 'var(--text-primary)', fontWeight: 600 }}>
            {passedGates}/{totalGates}
          </span>
        </div>
        <div style={{ height: 2, background: 'var(--border-default)', borderRadius: 1, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${progressPercent}%`, background: failedGates > 0 ? 'var(--signal-fail)' : 'var(--text-primary)', transition: 'width 400ms ease-out' }} />
        </div>
      </div>

      <div>
        <button
          onClick={() => setGatesExpanded(!gatesExpanded)}
          className="w-full flex items-center justify-between"
          style={{ fontSize: 12, color: 'var(--text-tertiary)', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 400, borderTop: '1px solid var(--border-default)', padding: 'var(--space-md) 0' }}
        >
          <span>{t('gates')} ({gates.length})</span>
          <span style={{ transition: 'transform 200ms ease-out', transform: gatesExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>▾</span>
        </button>

        {gatesExpanded && (
          <div className="overflow-auto" style={{ maxHeight: 500 }}>
            <table className="w-full" style={{ fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                  <th className="text-left" style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, padding: 'var(--space-sm) 0' }}>{t('gate')}</th>
                  <th className="text-left" style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, padding: 'var(--space-sm)' }}>{t('status')}</th>
                  <th className="text-left" style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, padding: 'var(--space-sm)' }}>{t('tool')}</th>
                  <th className="text-right" style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, padding: 'var(--space-sm) 0' }}>{t('time')}</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((gate) => (
                  <GateRow key={gate.id} gate={gate} isExpanded={expandedGate === gate.id} onToggle={() => setExpandedGate(expandedGate === gate.id ? null : gate.id)} />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalGates === 0 && !contractError && (
          <div className="py-8 text-center" style={{ fontSize: 14, color: 'var(--text-tertiary)', fontWeight: 400 }}>{t('noData')}</div>
        )}
      </div>
    </div>
  );
}

function GateRow({ gate, isExpanded, onToggle }: { gate: Gate; isExpanded: boolean; onToggle: () => void }) {
  return (
    <>
      <tr onClick={onToggle} className="cursor-pointer" style={{ borderBottom: '1px solid var(--border-default)', transition: 'background 200ms ease-out' }}
        onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-tertiary)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
      >
        <td style={{ color: gateColor(gate.status), fontWeight: 500, fontSize: 14, padding: 'var(--space-sm) 0' }}>{gate.id}</td>
        <td style={{ padding: 'var(--space-sm)' }}><StatusPill status={gate.status} compact /></td>
        <td style={{ color: 'var(--text-tertiary)', fontWeight: 400, fontSize: 14, padding: 'var(--space-sm)' }}>{gate.tool}</td>
        <td className="text-right" style={{ color: 'var(--text-tertiary)', fontWeight: 400, padding: 'var(--space-sm) 0' }}>{gate.elapsed}</td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={4} style={{ padding: 0 }}>
            <div className="font-mono" style={{ padding: 'var(--space-md) 0', fontSize: 12, color: 'var(--text-tertiary)', maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap', fontWeight: 400, borderTop: '1px solid var(--border-default)', borderBottom: '1px solid var(--border-default)' }}>
              {gate.log || '—'}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
