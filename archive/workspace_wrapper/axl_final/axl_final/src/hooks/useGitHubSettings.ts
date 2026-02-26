/**
 * useGitHubSettings — BFF-aware settings hook.
 *
 * SECURITY CONTRACT:
 *   - No token field. The GitHub PAT lives in the Cloudflare Worker secret only.
 *   - localStorage stores only: owner, repo, pollInterval.
 *   - isConfigured is determined by BFF healthz reachability, not by token presence.
 */
import { useState, useCallback, useEffect } from 'react';
import type { GitHubSettings } from '@/lib/types';
import { healthz } from '@/lib/api';

const STORAGE_KEY = 'axl-bff-settings';

// Settings stored in localStorage — NO token.
interface StoredSettings {
  owner: string;
  repo: string;
  pollInterval: number;
}

const DEFAULT_STORED: StoredSettings = {
  owner: 'neuron7x',
  repo: 'Agent-X-Lab',
  pollInterval: 30,
};

function load(): StoredSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...DEFAULT_STORED, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return DEFAULT_STORED;
}

function save(s: StoredSettings): void {
  // Explicitly exclude any token field in case old data is present
  const { owner, repo, pollInterval } = s;
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ owner, repo, pollInterval }));
}

/**
 * Migrate away from old key that stored a token.
 * On first load, remove legacy data and re-save without token.
 */
function migrate(): void {
  const OLD_KEY = 'axl-github-settings';
  try {
    const legacy = localStorage.getItem(OLD_KEY);
    if (legacy) {
      const parsed = JSON.parse(legacy);
      // Migrate non-token fields
      const migrated: StoredSettings = {
        owner: parsed.owner || DEFAULT_STORED.owner,
        repo: parsed.repo || DEFAULT_STORED.repo,
        pollInterval: parsed.pollInterval || DEFAULT_STORED.pollInterval,
      };
      // token is intentionally dropped
      save(migrated);
      localStorage.removeItem(OLD_KEY);
      console.info('[axl] Migrated settings from legacy key — token removed');
    }
  } catch { /* ignore */ }
}

export type BffStatus = 'UNKNOWN' | 'REACHABLE' | 'UNREACHABLE';

export function useGitHubSettings() {
  // Run migration on first mount
  useEffect(() => { migrate(); }, []);

  const [stored, setStored] = useState<StoredSettings>(load);
  const [bffStatus, setBffStatus] = useState<BffStatus>('UNKNOWN');

  // isConfigured = owner + repo set AND bff is reachable
  const isConfigured = Boolean(stored.owner && stored.repo) && bffStatus === 'REACHABLE';

  // Expose settings as GitHubSettings shape — token always ''
  const settings: GitHubSettings = {
    token: '',   // SECURITY: always empty — never from browser
    owner: stored.owner,
    repo: stored.repo,
    pollInterval: stored.pollInterval,
  };

  const updateSettings = useCallback((patch: Partial<Omit<GitHubSettings, 'token'>>) => {
    setStored(prev => {
      // Strip token if someone passes it (defense in depth)
      const { token: _ignored, ...safe } = patch as Partial<GitHubSettings>;
      void _ignored;
      const next = { ...prev, ...safe };
      save(next);
      return next;
    });
  }, []);

  const clearSettings = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setStored(DEFAULT_STORED);
    setBffStatus('UNKNOWN');
  }, []);

  /**
   * Probe BFF healthz to confirm reachability.
   * Called from ConnectRepository after user fills owner/repo.
   */
  const probeBff = useCallback(async (): Promise<boolean> => {
    try {
      await healthz();
      setBffStatus('REACHABLE');
      return true;
    } catch {
      setBffStatus('UNREACHABLE');
      return false;
    }
  }, []);

  // Auto-probe on mount if settings look valid
  useEffect(() => {
    if (stored.owner && stored.repo && bffStatus === 'UNKNOWN') {
      probeBff().catch(() => setBffStatus('UNREACHABLE'));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    settings,
    updateSettings,
    clearSettings,
    isConfigured,
    bffStatus,
    probeBff,
  };
}
