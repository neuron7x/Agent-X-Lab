/**
 * src/lib/useEvidenceFilter.ts
 * Phase 4.2: Evidence filter + search logic (extracted for testability).
 * Filters by status, type, sha prefix, text search, time window.
 */
import { useMemo, useState } from 'react';
import type { EvidenceEntry } from '@/lib/schemas';

export type StatusFilter = 'ALL' | 'PASS' | 'FAIL' | 'UNKNOWN';

export interface EvidenceFilters {
  status: StatusFilter;
  search: string;        // text search: matches type, sha, message, path
  timeWindowH: number;   // hours back (0 = all time)
}

export const DEFAULT_FILTERS: EvidenceFilters = {
  status: 'ALL',
  search: '',
  timeWindowH: 0,
};

export function useEvidenceFilter(entries: EvidenceEntry[]) {
  const [filters, setFilters] = useState<EvidenceFilters>(DEFAULT_FILTERS);

  const filtered = useMemo(() => {
    let result = entries;

    // Status filter
    if (filters.status !== 'ALL') {
      result = result.filter(e => {
        if (filters.status === 'UNKNOWN') return e.status === 'UNKNOWN' || e.status === 'ASSUMED';
        return e.status === filters.status;
      });
    }

    // Time window
    if (filters.timeWindowH > 0) {
      const cutoff = Date.now() - filters.timeWindowH * 3_600_000;
      result = result.filter(e => {
        if (!e.timestamp) return true;
        const ts = new Date(e.timestamp).getTime();
        return !isNaN(ts) && ts >= cutoff;
      });
    }

    // Text search
    if (filters.search.trim()) {
      const q = filters.search.trim().toLowerCase();
      result = result.filter(e => {
        const fields = [e.type, e.sha, e.message, e.path].filter(Boolean).map(s => s!.toLowerCase());
        return fields.some(f => f.includes(q));
      });
    }

    return result;
  }, [entries, filters]);

  const counts = useMemo(() => ({
    total: entries.length,
    shown: filtered.length,
    pass:  entries.filter(e => e.status === 'PASS').length,
    fail:  entries.filter(e => e.status === 'FAIL').length,
  }), [entries, filtered.length]);

  return { filters, setFilters, filtered, counts };
}
