import { describe, it, expect } from 'vitest';
import { mapJobToGateStatus, jobElapsed, parseEvidenceLines } from '@/lib/github';
import { translations } from '@/lib/i18n';

// ── mapJobToGateStatus ──

describe('mapJobToGateStatus', () => {
  it('returns PASS for success conclusion', () => {
    expect(mapJobToGateStatus({ id: 1, name: 'test', status: 'completed', conclusion: 'success', started_at: null, completed_at: null })).toBe('PASS');
  });

  it('returns FAIL for failure conclusion', () => {
    expect(mapJobToGateStatus({ id: 1, name: 'test', status: 'completed', conclusion: 'failure', started_at: null, completed_at: null })).toBe('FAIL');
  });

  it('returns FAIL for cancelled conclusion', () => {
    expect(mapJobToGateStatus({ id: 1, name: 'test', status: 'completed', conclusion: 'cancelled', started_at: null, completed_at: null })).toBe('FAIL');
  });

  it('returns FAIL for timed_out conclusion', () => {
    expect(mapJobToGateStatus({ id: 1, name: 'test', status: 'completed', conclusion: 'timed_out', started_at: null, completed_at: null })).toBe('FAIL');
  });

  it('returns FAIL for action_required conclusion', () => {
    expect(mapJobToGateStatus({ id: 1, name: 'test', status: 'completed', conclusion: 'action_required', started_at: null, completed_at: null })).toBe('FAIL');
  });

  it('returns RUNNING for in_progress status', () => {
    expect(mapJobToGateStatus({ id: 1, name: 'test', status: 'in_progress', conclusion: null, started_at: null, completed_at: null })).toBe('RUNNING');
  });

  it('returns RUNNING for queued status', () => {
    expect(mapJobToGateStatus({ id: 1, name: 'test', status: 'queued', conclusion: null, started_at: null, completed_at: null })).toBe('RUNNING');
  });

  it('returns PENDING for null job', () => {
    expect(mapJobToGateStatus(null)).toBe('PENDING');
  });

  it('returns PENDING for neutral/skipped conclusion', () => {
    expect(mapJobToGateStatus({ id: 1, name: 'test', status: 'completed', conclusion: 'neutral', started_at: null, completed_at: null })).toBe('PENDING');
    expect(mapJobToGateStatus({ id: 1, name: 'test', status: 'completed', conclusion: 'skipped', started_at: null, completed_at: null })).toBe('PENDING');
  });
});

// ── jobElapsed ──

describe('jobElapsed', () => {
  it('returns "—" for null job', () => {
    expect(jobElapsed(null)).toBe('—');
  });

  it('returns "—" when started_at or completed_at is null', () => {
    expect(jobElapsed({ id: 1, name: 'test', status: 'completed', conclusion: 'success', started_at: null, completed_at: null })).toBe('—');
    expect(jobElapsed({ id: 1, name: 'test', status: 'completed', conclusion: 'success', started_at: '2026-01-01T00:00:00Z', completed_at: null })).toBe('—');
  });

  it('formats <60s correctly', () => {
    expect(jobElapsed({ id: 1, name: 'test', status: 'completed', conclusion: 'success', started_at: '2026-01-01T00:00:00Z', completed_at: '2026-01-01T00:00:45Z' })).toBe('45s');
  });

  it('formats >=60s correctly', () => {
    expect(jobElapsed({ id: 1, name: 'test', status: 'completed', conclusion: 'success', started_at: '2026-01-01T00:00:00Z', completed_at: '2026-01-01T00:01:30Z' })).toBe('1m30s');
  });

  it('formats exactly 60s', () => {
    expect(jobElapsed({ id: 1, name: 'test', status: 'completed', conclusion: 'success', started_at: '2026-01-01T00:00:00Z', completed_at: '2026-01-01T00:01:00Z' })).toBe('1m00s');
  });
  it('returns "—" for invalid timestamps', () => {
    expect(jobElapsed({ id: 1, name: 'test', status: 'completed', conclusion: 'success', started_at: 'invalid', completed_at: '2026-01-01T00:01:00Z' })).toBe('—');
    expect(jobElapsed({ id: 1, name: 'test', status: 'completed', conclusion: 'success', started_at: '2026-01-01T00:00:00Z', completed_at: 'invalid' })).toBe('—');
  });

});

// ── parseEvidenceLines ──

describe('parseEvidenceLines', () => {
  it('parses valid JSONL lines', () => {
    const text = '{"ts":"12:00","command":"test","exit":0,"sha":"abcdef12"}\n{"ts":"12:01","command":"lint","status":"FAIL","sha":"deadbeef"}';
    const result = parseEvidenceLines(text);
    expect(result.entries).toHaveLength(2);
    expect(result.parseFailures).toBe(0);
    // newest-first (reversed)
    expect(result.entries[0].type).toBe('lint');
    expect(result.entries[0].status).toBe('FAIL');
    expect(result.entries[1].type).toBe('test');
    expect(result.entries[1].status).toBe('PASS');
  });

  it('ignores empty lines', () => {
    const text = '{"ts":"12:00","command":"test","exit":0}\n\n\n';
    const result = parseEvidenceLines(text);
    expect(result.entries).toHaveLength(1);
    expect(result.parseFailures).toBe(0);
  });

  it('counts malformed lines as parseFailures', () => {
    const text = '{"ts":"12:00","command":"test","exit":0}\n{INVALID JSON}\nnot json at all';
    const result = parseEvidenceLines(text);
    expect(result.entries).toHaveLength(1);
    expect(result.parseFailures).toBe(2);
  });

  it('limits to 30 entries', () => {
    const lines = Array.from({ length: 50 }, (_, i) => `{"ts":"${i}","command":"cmd${i}","exit":0}`).join('\n');
    const result = parseEvidenceLines(lines);
    expect(result.entries).toHaveLength(30);
  });

  it('maps exit=0 to PASS, exit!=0 to FAIL', () => {
    const text = '{"ts":"1","command":"a","exit":0}\n{"ts":"2","command":"b","exit":1}';
    const result = parseEvidenceLines(text);
    // reversed: b first, a second
    expect(result.entries[0].status).toBe('FAIL');
    expect(result.entries[1].status).toBe('PASS');
  });

  it('maps missing exit and status to ASSUMED', () => {
    const text = '{"ts":"1","command":"a"}';
    const result = parseEvidenceLines(text);
    expect(result.entries[0].status).toBe('ASSUMED');
  });
});

// ── i18n completeness ──

describe('i18n completeness', () => {
  it('UA and EN have identical key sets', () => {
    const keys = Object.keys(translations) as Array<keyof typeof translations>;
    for (const key of keys) {
      const entry = translations[key];
      expect(entry).toHaveProperty('ua', expect.any(String));
      expect(entry).toHaveProperty('en', expect.any(String));
      expect((entry as Record<string, string>).ua.length).toBeGreaterThan(0);
      expect((entry as Record<string, string>).en.length).toBeGreaterThan(0);
    }
  });
});
