import { useState } from 'react';
import type { EvidenceEntry } from '@/lib/types';

const STATUS_COLORS: Record<string, string> = {
  PASS: '#00e87a',
  FAIL: '#ff2d55',
  ASSUMED: '#aa66ff',
  RUNNING: '#4488ff',
  PENDING: '#666688',
};

interface EvidenceFeedProps {
  entries: EvidenceEntry[];
}

export function EvidenceFeed({ entries }: EvidenceFeedProps) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  return (
    <div className="axl-panel p-4" style={{ animation: 'stagger-reveal 0.3s ease-out forwards', animationDelay: '160ms' }}>
      <h2 className="axl-label mb-3" style={{ fontSize: '12px' }}>EVIDENCE FEED</h2>

      {entries.length === 0 ? (
        <div className="flex items-center justify-center h-24">
          <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-dim)' }}>NO DATA</span>
        </div>
      ) : (
        <div className="flex flex-col gap-0 overflow-auto" style={{ maxHeight: '360px' }}>
          {entries.map((entry, i) => {
            const color = STATUS_COLORS[entry.status] || '#666688';
            const isExpanded = expandedIdx === i;
            return (
              <div
                key={i}
                onClick={() => setExpandedIdx(isExpanded ? null : i)}
                className="cursor-pointer py-2 px-1"
                style={{
                  borderBottom: '1px solid var(--border-dim)',
                  animation: `scan-line 0.15s ease-out forwards`,
                  animationDelay: `${i * 40}ms`,
                }}
              >
                <div className="flex items-center gap-2">
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} aria-label={`Evidence ${entry.status}`} />
                  <span className="font-mono" style={{ fontSize: '10px', color: 'var(--text-dim)' }}>{entry.timestamp}</span>
                  <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-primary)' }}>{entry.type}</span>
                  <span className="ml-auto font-mono" style={{ fontSize: '10px', color }}>{entry.status}</span>
                </div>
                <div className="font-mono mt-1" style={{ fontSize: '9px', color: 'var(--text-dim)', paddingLeft: 14 }}>
                  {isExpanded ? entry.path : entry.sha}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
