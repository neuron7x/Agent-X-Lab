/**
 * src/components/axl/EvidenceFilterBar.tsx
 * Phase 4.2: Evidence filter UI (search, status badge buttons, time window).
 * Phase 6: triggers virtual list rendering when > threshold items.
 * I5: keyboard accessible — all controls have aria-labels.
 */
import type { EvidenceFilters, StatusFilter } from '@/lib/useEvidenceFilter';

const STATUS_OPTIONS: { value: StatusFilter; label: string; color: string }[] = [
  { value: 'ALL',     label: 'ALL',     color: 'var(--text-secondary,#aaa)' },
  { value: 'PASS',    label: 'PASS',    color: 'var(--signal-pass,#00e87a)' },
  { value: 'FAIL',    label: 'FAIL',    color: 'var(--signal-fail,#ff3b30)' },
  { value: 'UNKNOWN', label: '?',       color: 'var(--text-tertiary,#555)' },
];

const TIME_OPTIONS: { value: number; label: string }[] = [
  { value: 0,   label: 'All time' },
  { value: 1,   label: '1h' },
  { value: 6,   label: '6h' },
  { value: 24,  label: '24h' },
  { value: 168, label: '7d' },
];

interface Props {
  filters: EvidenceFilters;
  onChange: (f: EvidenceFilters) => void;
  counts: { total: number; shown: number; pass: number; fail: number };
  lang?: 'ua' | 'en';
}

export function EvidenceFilterBar({ filters, onChange, counts, lang = 'en' }: Props) {
  return (
    <div
      role="search"
      aria-label={lang === 'ua' ? 'Фільтр доказів' : 'Evidence filter'}
      style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12, alignItems: 'center' }}
    >
      {/* Text search */}
      <input
        type="search"
        aria-label={lang === 'ua' ? 'Пошук доказів' : 'Search evidence'}
        placeholder={lang === 'ua' ? 'Пошук: тип, sha, шлях…' : 'Search: type, sha, path…'}
        value={filters.search}
        onChange={e => onChange({ ...filters, search: e.target.value })}
        style={{
          flex: '1 1 140px', minWidth: 120,
          fontSize: 12, fontFamily: 'monospace',
          background: 'var(--bg-tertiary,#111)',
          color: 'var(--text-primary,#fff)',
          border: '1px solid var(--border-dim,#333)',
          borderRadius: 4, padding: '4px 8px', outline: 'none',
        }}
      />

      {/* Status filters */}
      <div role="group" aria-label="Status filter" style={{ display: 'flex', gap: 4 }}>
        {STATUS_OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => onChange({ ...filters, status: opt.value })}
            aria-pressed={filters.status === opt.value}
            style={{
              fontSize: 10, fontWeight: 700, fontFamily: 'monospace',
              padding: '3px 8px', borderRadius: 3, cursor: 'pointer',
              border: `1px solid ${filters.status === opt.value ? opt.color : 'var(--border-dim,#333)'}`,
              background: filters.status === opt.value ? 'var(--bg-tertiary,#111)' : 'transparent',
              color: opt.color,
              transition: 'border-color 150ms',
            }}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Time window */}
      <select
        aria-label={lang === 'ua' ? 'Часовий діапазон' : 'Time window'}
        value={filters.timeWindowH}
        onChange={e => onChange({ ...filters, timeWindowH: Number(e.target.value) })}
        style={{
          fontSize: 11, fontFamily: 'monospace',
          background: 'var(--bg-tertiary,#111)',
          color: 'var(--text-secondary,#aaa)',
          border: '1px solid var(--border-dim,#333)',
          borderRadius: 4, padding: '4px 6px', outline: 'none',
        }}
      >
        {TIME_OPTIONS.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>

      {/* Stats */}
      <span style={{ fontSize: 11, color: 'var(--text-tertiary,#555)', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
        {counts.shown}/{counts.total}
        {counts.fail > 0 && <> · <span style={{ color: 'var(--signal-fail,#ff3b30)' }}>{counts.fail}F</span></>}
        {counts.pass > 0 && <> · <span style={{ color: 'var(--signal-pass,#00e87a)' }}>{counts.pass}P</span></>}
      </span>
    </div>
  );
}
