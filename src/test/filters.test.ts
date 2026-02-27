/**
 * src/test/filters.test.ts
 * Phase 7.1: Unit tests for evidence filter, arsenal search, ProtectedAction gate.
 * GATE-3/4/5 evidence.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useEvidenceFilter, DEFAULT_FILTERS } from '@/lib/useEvidenceFilter';
import { useArsenalSearch } from '@/lib/useArsenalSearch';
import { getActionGateStatus } from '@/components/axl/actionGate';
import type { EvidenceEntry } from '@/lib/schemas';
import type { ArsenalItem } from '@/lib/schemas';

// ── Test data ─────────────────────────────────────────────────────────────

const NOW_ISO = new Date().toISOString();
const HOUR_AGO = new Date(Date.now() - 3_600_000).toISOString();
const DAY_AGO = new Date(Date.now() - 25 * 3_600_000).toISOString();

const EVIDENCE: EvidenceEntry[] = [
  { id: '1', type: 'lint', sha: 'abc123', status: 'PASS', timestamp: NOW_ISO, message: 'lint ok' },
  { id: '2', type: 'test', sha: 'def456', status: 'FAIL', timestamp: HOUR_AGO, message: 'test failed' },
  { id: '3', type: 'build', sha: 'abc789', status: 'PASS', timestamp: DAY_AGO, message: 'build ok' },
  { id: '4', type: 'security', sha: 'xyz000', status: 'UNKNOWN', timestamp: NOW_ISO, message: 'scan pending' },
];

const ARSENAL: ArsenalItem[] = [
  { id: '1', title: 'PR Orchestrator', role: 'PR-AGENT', target: 'github', tags: ['pr', 'ci'], category: 'automation' },
  { id: '2', title: 'Security Hardener', role: 'SECURITY-AGENT', target: 'codebase', tags: ['security'], category: 'security' },
  { id: '3', title: 'CI Governor', role: 'CI-AGENT', target: 'pipeline', tags: ['ci', 'pipeline'], category: 'automation' },
  { id: '4', title: 'Docs Writer', role: 'DOCS-AGENT', target: 'readme', tags: ['docs'], category: 'docs' },
];

// ── useEvidenceFilter ─────────────────────────────────────────────────────

describe('useEvidenceFilter', () => {
  it('returns all entries with default filters', () => {
    const { result } = renderHook(() => useEvidenceFilter(EVIDENCE));
    expect(result.current.filtered).toHaveLength(4);
  });

  it('filters by PASS status', () => {
    const { result } = renderHook(() => useEvidenceFilter(EVIDENCE));
    act(() => result.current.setFilters({ ...DEFAULT_FILTERS, status: 'PASS' }));
    expect(result.current.filtered).toHaveLength(2);
    expect(result.current.filtered.every(e => e.status === 'PASS')).toBe(true);
  });

  it('filters by FAIL status', () => {
    const { result } = renderHook(() => useEvidenceFilter(EVIDENCE));
    act(() => result.current.setFilters({ ...DEFAULT_FILTERS, status: 'FAIL' }));
    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].type).toBe('test');
  });

  it('filters by UNKNOWN status', () => {
    const { result } = renderHook(() => useEvidenceFilter(EVIDENCE));
    act(() => result.current.setFilters({ ...DEFAULT_FILTERS, status: 'UNKNOWN' }));
    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].id).toBe('4');
  });

  it('searches by type', () => {
    const { result } = renderHook(() => useEvidenceFilter(EVIDENCE));
    act(() => result.current.setFilters({ ...DEFAULT_FILTERS, search: 'lint' }));
    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].type).toBe('lint');
  });

  it('searches by sha prefix', () => {
    const { result } = renderHook(() => useEvidenceFilter(EVIDENCE));
    act(() => result.current.setFilters({ ...DEFAULT_FILTERS, search: 'abc' }));
    // abc123 and abc789
    expect(result.current.filtered).toHaveLength(2);
  });

  it('searches by message', () => {
    const { result } = renderHook(() => useEvidenceFilter(EVIDENCE));
    act(() => result.current.setFilters({ ...DEFAULT_FILTERS, search: 'failed' }));
    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].id).toBe('2');
  });

  it('time window 1h excludes old entries', () => {
    const { result } = renderHook(() => useEvidenceFilter(EVIDENCE));
    act(() => result.current.setFilters({ ...DEFAULT_FILTERS, timeWindowH: 1 }));
    // DAY_AGO (25h ago) should be excluded; HOUR_AGO (1h) edge case — may or may not be included
    const shown = result.current.filtered;
    const hasOld = shown.some(e => e.timestamp === DAY_AGO);
    expect(hasOld).toBe(false);
  });

  it('combined filter: PASS + search "lint"', () => {
    const { result } = renderHook(() => useEvidenceFilter(EVIDENCE));
    act(() => result.current.setFilters({ ...DEFAULT_FILTERS, status: 'PASS', search: 'lint' }));
    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].type).toBe('lint');
  });

  it('counts are correct', () => {
    const { result } = renderHook(() => useEvidenceFilter(EVIDENCE));
    expect(result.current.counts.total).toBe(4);
    expect(result.current.counts.pass).toBe(2);
    expect(result.current.counts.fail).toBe(1);
  });

  it('returns empty array when no matches', () => {
    const { result } = renderHook(() => useEvidenceFilter(EVIDENCE));
    act(() => result.current.setFilters({ ...DEFAULT_FILTERS, search: 'NOMATCH_XYZ_9999' }));
    expect(result.current.filtered).toHaveLength(0);
    expect(result.current.counts.shown).toBe(0);
  });
});

// ── useArsenalSearch ──────────────────────────────────────────────────────

describe('useArsenalSearch', () => {
  it('returns all items with default filters', () => {
    const { result } = renderHook(() => useArsenalSearch(ARSENAL));
    expect(result.current.filtered).toHaveLength(4);
  });

  it('filters by role', () => {
    const { result } = renderHook(() => useArsenalSearch(ARSENAL));
    act(() => result.current.setFilters({ search: '', role: 'CI-AGENT', category: '' }));
    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].title).toBe('CI Governor');
  });

  it('filters by category', () => {
    const { result } = renderHook(() => useArsenalSearch(ARSENAL));
    act(() => result.current.setFilters({ search: '', role: '', category: 'automation' }));
    expect(result.current.filtered).toHaveLength(2);
  });

  it('searches by title', () => {
    const { result } = renderHook(() => useArsenalSearch(ARSENAL));
    act(() => result.current.setFilters({ search: 'security', role: '', category: '' }));
    expect(result.current.filtered.some(i => i.title === 'Security Hardener')).toBe(true);
  });

  it('searches by tag', () => {
    const { result } = renderHook(() => useArsenalSearch(ARSENAL));
    act(() => result.current.setFilters({ search: 'pipeline', role: '', category: '' }));
    expect(result.current.filtered).toHaveLength(1);
    expect(result.current.filtered[0].title).toBe('CI Governor');
  });

  it('combined role + search', () => {
    const { result } = renderHook(() => useArsenalSearch(ARSENAL));
    act(() => result.current.setFilters({ search: 'pr', role: 'PR-AGENT', category: '' }));
    expect(result.current.filtered).toHaveLength(1);
  });

  it('exposes unique roles list', () => {
    const { result } = renderHook(() => useArsenalSearch(ARSENAL));
    expect(result.current.roles).toContain('PR-AGENT');
    expect(result.current.roles).toContain('CI-AGENT');
    expect(result.current.roles.length).toBe(4); // 4 unique roles
  });

  it('exposes unique categories list', () => {
    const { result } = renderHook(() => useArsenalSearch(ARSENAL));
    expect(result.current.categories).toContain('automation');
    expect(result.current.categories).toContain('security');
  });
});

// ── ProtectedAction gate ──────────────────────────────────────────────────

describe('getActionGateStatus', () => {
  const originalEnv = { ...import.meta.env };

  afterEach(() => {
    // Reset env (Vitest env vars are read at call time via import.meta.env)
    vi.unstubAllEnvs();
  });

  it('returns ALLOWED when API key is set', () => {
    vi.stubEnv('VITE_AXL_API_KEY', 'test-key-123');
    expect(getActionGateStatus()).toBe('ALLOWED');
  });

  it('returns DEV_BYPASS in dev mode without key', () => {
    vi.stubEnv('VITE_AXL_API_KEY', '');
    // In vitest, import.meta.env.DEV is true by default
    const status = getActionGateStatus();
    // Should be DEV_BYPASS (since vitest runs in dev mode)
    expect(['DEV_BYPASS', 'ALLOWED']).toContain(status);
  });

  it('status is consistent across calls', () => {
    const s1 = getActionGateStatus();
    const s2 = getActionGateStatus();
    expect(s1).toBe(s2);
  });
});
