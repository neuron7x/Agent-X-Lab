import { useState } from 'react';
import type { Gate } from '@/lib/types';
import { StatusPill } from './StatusPill';

interface GateTableProps {
  gates: Gate[];
}

const STATUS_ORDER = { FAIL: 0, BLOCKED: 1, ASSUMED: 2, RUNNING: 3, PENDING: 4, PASS: 5 };

export function GateTable({ gates }: GateTableProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const sorted = [...gates].sort((a, b) => (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9));

  if (gates.length === 0) {
    return (
      <div className="axl-panel" style={{ padding: 'var(--space-lg)' }}>
        <h3 className="axl-label" style={{ fontSize: 14, marginBottom: 'var(--space-md)' }}>GATE TABLE</h3>
        <div className="flex items-center justify-center h-16">
          <span style={{ fontSize: 14, color: 'var(--text-tertiary)' }}>NO DATA</span>
        </div>
      </div>
    );
  }

  return (
    <div className="axl-panel" style={{ animation: 'stagger-reveal 300ms ease forwards' }}>
      <div style={{ padding: 'var(--space-md) var(--space-lg) 0' }}>
        <h3 className="axl-label" style={{ fontSize: 14, marginBottom: 'var(--space-sm)' }}>GATE TABLE</h3>
      </div>
      <div className="overflow-auto" style={{ maxHeight: 340 }}>
        <table className="w-full" style={{ fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
              <th className="text-left axl-label" style={{ fontSize: 12, padding: 'var(--space-sm) var(--space-md)' }}>GATE ID</th>
              <th className="text-left axl-label" style={{ fontSize: 12, padding: 'var(--space-sm) var(--space-md)' }}>STATUS</th>
              <th className="text-left axl-label" style={{ fontSize: 12, padding: 'var(--space-sm) var(--space-md)' }}>TOOL</th>
              <th className="text-right axl-label" style={{ fontSize: 12, padding: 'var(--space-sm) var(--space-md)' }}>ELAPSED</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((gate) => (
              <GateRow
                key={gate.id}
                gate={gate}
                isExpanded={expanded === gate.id}
                onToggle={() => setExpanded(expanded === gate.id ? null : gate.id)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function GateRow({ gate, isExpanded, onToggle }: { gate: Gate; isExpanded: boolean; onToggle: () => void }) {
  return (
    <>
      <tr
        onClick={onToggle}
        className="cursor-pointer"
        style={{ borderBottom: '1px solid var(--border-default)', transition: 'background 200ms ease-out' }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-tertiary)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
      >
        <td style={{ padding: 'var(--space-sm) var(--space-md)', color: 'var(--text-primary)' }}>{gate.id}</td>
        <td style={{ padding: 'var(--space-sm) var(--space-md)' }}><StatusPill status={gate.status} compact /></td>
        <td style={{ padding: 'var(--space-sm) var(--space-md)', color: 'var(--text-secondary)' }}>{gate.tool}</td>
        <td className="text-right" style={{ padding: 'var(--space-sm) var(--space-md)', color: 'var(--text-tertiary)' }}>{gate.elapsed}</td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={4} style={{ padding: 0 }}>
            <div
              className="font-mono"
              style={{
                background: 'var(--bg-tertiary)',
                padding: 'var(--space-md) var(--space-lg)',
                fontSize: 12,
                color: 'var(--text-tertiary)',
                maxHeight: 200,
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                borderTop: '1px solid var(--border-default)',
                borderBottom: '1px solid var(--border-default)',
              }}
            >
              {gate.log || 'No log available'}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
