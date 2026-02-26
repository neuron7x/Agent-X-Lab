/**
 * ConnectRepository — BFF-aware connect screen.
 *
 * SECURITY CONTRACT:
 *   - No PAT/token field. Zero secrets in the browser.
 *   - User provides only: owner, repo (public identifiers).
 *   - Connection is verified via BFF /healthz probe.
 */
import { useState } from 'react';
import type { GitHubSettings } from '@/lib/types';
import { useLanguage } from '@/hooks/useLanguage';
import type { BffStatus } from '@/hooks/useGitHubSettings';

interface ConnectRepositoryProps {
  onConnect: (settings: Partial<Omit<GitHubSettings, 'token'>>, probe: () => Promise<boolean>) => void;
  onPreviewDemo: () => void;
  bffStatus: BffStatus;
}

export function ConnectRepository({ onConnect, onPreviewDemo, bffStatus }: ConnectRepositoryProps) {
  const { t } = useLanguage();
  const [owner, setOwner] = useState('neuron7x');
  const [repo, setRepo] = useState('Agent-X-Lab');
  const [probing, setProbing] = useState(false);
  const [probeError, setProbeError] = useState<string | null>(null);

  const inputStyle: React.CSSProperties = {
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    color: 'var(--text-primary)',
    fontFamily: 'inherit',
    fontSize: 14,
    padding: '12px 16px',
    width: '100%',
    borderRadius: 12,
    outline: 'none',
    fontWeight: 400,
    transition: 'border-color 200ms ease-out',
    height: 48,
  };

  const canSubmit = Boolean(owner && repo && !probing);

  const handleConnect = async (probe: () => Promise<boolean>) => {
    setProbing(true);
    setProbeError(null);
    try {
      const ok = await probe();
      if (!ok) {
        setProbeError('BFF_UNREACHABLE');
        return;
      }
      onConnect({ owner, repo }, probe);
    } catch {
      setProbeError('BFF_UNREACHABLE');
    } finally {
      setProbing(false);
    }
  };

  const bffApiBase = (import.meta.env?.VITE_AXL_API_BASE as string | undefined) ?? '(not set)';

  return (
    <div className="flex items-center justify-center" style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <div className="axl-panel" style={{ width: 420, padding: 'var(--space-2xl)', animation: 'stagger-reveal 300ms ease forwards' }}>
        <div className="text-center" style={{ marginBottom: 'var(--space-2xl)' }}>
          <div style={{ fontSize: 20, color: 'var(--text-primary)', fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
            AGENT-X-LAB
          </div>
          <p style={{ fontSize: 14, color: 'var(--text-tertiary)', fontWeight: 400 }}>
            {t('connectToAgentXLab')}
          </p>
        </div>

        {/* BFF status indicator */}
        <div style={{
          marginBottom: 'var(--space-lg)',
          padding: '8px 12px',
          borderRadius: 8,
          border: '1px solid var(--border-dim)',
          background: 'var(--bg-elevated)',
          fontSize: 11,
          fontFamily: "'JetBrains Mono', monospace",
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span style={{
            color: bffStatus === 'REACHABLE' ? 'var(--signal-pass)'
              : bffStatus === 'UNREACHABLE' ? 'var(--signal-fail)'
              : 'var(--signal-warn)',
          }}>●</span>
          <span style={{ color: 'var(--text-secondary)' }}>BFF:</span>
          <span style={{ color: 'var(--text-primary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {bffApiBase}
          </span>
          <span style={{
            color: bffStatus === 'REACHABLE' ? 'var(--signal-pass)'
              : bffStatus === 'UNREACHABLE' ? 'var(--signal-fail)'
              : 'var(--text-dim)',
          }}>
            {bffStatus}
          </span>
        </div>

        <div className="flex flex-col" style={{ gap: 'var(--space-md)', marginBottom: 'var(--space-xl)' }}>
          <label>
            <span className="block" style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginBottom: 'var(--space-xs)' }}>
              {t('owner')}
            </span>
            <input
              type="text"
              value={owner}
              onChange={e => setOwner(e.target.value)}
              style={inputStyle}
              placeholder="neuron7x"
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--text-primary)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-default)'; }}
            />
          </label>
          <label>
            <span className="block" style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginBottom: 'var(--space-xs)' }}>
              {t('repository')}
            </span>
            <input
              type="text"
              value={repo}
              onChange={e => setRepo(e.target.value)}
              style={inputStyle}
              placeholder="Agent-X-Lab"
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--text-primary)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-default)'; }}
            />
          </label>
        </div>

        {probeError && (
          <div style={{ marginBottom: 'var(--space-md)', fontSize: 12, color: 'var(--signal-fail)', fontFamily: "'JetBrains Mono', monospace" }}>
            ✕ BFF unreachable. Check VITE_AXL_API_BASE and Worker deployment.
          </div>
        )}

        <button
          onClick={() => {
            // probe fn passed in — component calls it, reports result
            handleConnect(async () => {
              // We call probeBff from parent scope via onConnect callback pattern
              // Use a temporary fetch to healthz to avoid coupling
              try {
                const base = (import.meta.env?.VITE_AXL_API_BASE as string | undefined) ?? 'http://localhost:8787';
                const res = await fetch(`${base.replace(/\/$/, '')}/healthz`, { credentials: 'omit' });
                return res.ok;
              } catch { return false; }
            });
          }}
          disabled={!canSubmit}
          className="axl-surface w-full"
          style={{
            fontSize: 14, padding: '12px', fontWeight: 500,
            cursor: canSubmit ? 'pointer' : 'default', borderRadius: 999,
            marginBottom: 'var(--space-sm)', opacity: canSubmit ? 1 : 0.4,
          }}
        >
          {probing ? '…' : t('connect')}
        </button>

        <button
          onClick={onPreviewDemo}
          className="axl-surface w-full"
          style={{ fontSize: 12, padding: '10px', fontWeight: 400, cursor: 'pointer', borderRadius: 999 }}
        >
          {t('previewDemo')}
        </button>

        {/* Security notice */}
        <p style={{ marginTop: 'var(--space-lg)', fontSize: 10, color: 'var(--text-dim)', textAlign: 'center', fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.6 }}>
          No token required. GitHub auth is handled server-side by the BFF Worker.
        </p>
      </div>
    </div>
  );
}
