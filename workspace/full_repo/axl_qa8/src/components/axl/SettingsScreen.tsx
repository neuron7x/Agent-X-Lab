/**
 * SettingsScreen — full-page settings (tab view).
 * SECURITY: No PAT/token field. Auth is server-side in BFF Worker.
 */
import { useState } from 'react';
import type { GitHubSettings } from '@/lib/types';
import { healthz } from '@/lib/api';
import { useLanguage } from '@/hooks/useLanguage';

interface SettingsScreenProps {
  settings: GitHubSettings;
  onUpdateSettings: (patch: Partial<Omit<GitHubSettings, 'token'>>) => void;
  onClearSettings: () => void;
  lastVerified: string | null;
  isDemoMode?: boolean;
  onExitDemo?: () => void;
}

export function SettingsScreen({
  settings, onUpdateSettings, onClearSettings,
  lastVerified, isDemoMode, onExitDemo,
}: SettingsScreenProps) {
  const { t, lang, setLang } = useLanguage();
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<boolean | null>(null);
  const [localOwner, setLocalOwner] = useState(settings.owner);
  const [localRepo, setLocalRepo] = useState(settings.repo);

  const handleSave = () => {
    onUpdateSettings({ owner: localOwner, repo: localRepo });
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      await healthz();
      setTestResult(true);
    } catch {
      setTestResult(false);
    }
    setTesting(false);
  };

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

  const bffBase = (import.meta.env?.VITE_AXL_API_BASE as string | undefined) ?? '(not set)';

  return (
    <div className="flex flex-col" style={{ minHeight: 'calc(100vh - 104px)', padding: 'var(--space-xl)', maxWidth: 480, margin: '0 auto' }}>
      <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 'var(--space-2xl)' }}>
        {t('settings')}
      </h1>

      {/* Language toggle */}
      <div className="axl-panel" style={{ padding: 'var(--space-lg)', marginBottom: 'var(--space-lg)' }}>
        <h3 style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginBottom: 'var(--space-md)' }}>
          {t('language')}
        </h3>
        <div className="flex gap-2">
          {(['ua', 'en'] as const).map(l => (
            <button key={l} onClick={() => setLang(l)} style={{
              fontSize: 14, padding: '8px 20px',
              background: lang === l ? 'var(--bg-quaternary)' : 'transparent',
              cursor: 'pointer', borderRadius: 999,
              fontWeight: lang === l ? 600 : 400,
              color: lang === l ? 'var(--text-primary)' : 'var(--text-tertiary)',
              border: `1px solid ${lang === l ? 'var(--text-primary)' : 'var(--border-default)'}`,
              transition: 'all 200ms ease-out',
            }}>
              {l.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {isDemoMode && (
        <div className="axl-panel flex items-center justify-between" style={{ padding: 'var(--space-lg)', marginBottom: 'var(--space-lg)' }}>
          <div>
            <span style={{ fontSize: 14, color: 'var(--text-primary)', fontWeight: 600 }}>{t('demoMode')}</span>
            <p style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginTop: 'var(--space-xs)' }}>
              {t('viewingMockData')}
            </p>
          </div>
          {onExitDemo && (
            <button onClick={onExitDemo} className="axl-surface" style={{ fontSize: 12, padding: '8px 16px', borderRadius: 999, fontWeight: 400, cursor: 'pointer' }}>
              {t('exitDemo')}
            </button>
          )}
        </div>
      )}

      {/* BFF endpoint (read-only) */}
      <div className="axl-panel" style={{ padding: 'var(--space-lg)', marginBottom: 'var(--space-lg)' }}>
        <h3 style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginBottom: 'var(--space-md)' }}>
          BFF ENDPOINT
        </h3>
        <div style={{
          fontSize: 11, padding: '10px 14px',
          background: 'var(--bg-elevated)', border: '1px solid var(--border-dim)',
          borderRadius: 8, color: 'var(--text-secondary)',
          fontFamily: "'JetBrains Mono', monospace",
          wordBreak: 'break-all',
        }}>
          {bffBase}
        </div>
        <p style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 6, fontFamily: "'JetBrains Mono', monospace" }}>
          Configured via VITE_AXL_API_BASE. GitHub auth is server-side — no token in browser.
        </p>
      </div>

      {/* Repo config */}
      <div className="axl-panel" style={{ padding: 'var(--space-lg)', marginBottom: 'var(--space-lg)' }}>
        <h3 style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginBottom: 'var(--space-lg)' }}>
          {t('github')}
        </h3>

        <label className="block" style={{ marginBottom: 'var(--space-md)' }}>
          <span className="block" style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginBottom: 'var(--space-xs)' }}>
            {t('owner')}
          </span>
          <input type="text" value={localOwner} onChange={e => setLocalOwner(e.target.value)}
            style={inputStyle} placeholder="neuron7x"
            onFocus={e => { e.currentTarget.style.borderColor = 'var(--text-primary)'; }}
            onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-default)'; }}
          />
        </label>
        <label className="block" style={{ marginBottom: 'var(--space-md)' }}>
          <span className="block" style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginBottom: 'var(--space-xs)' }}>
            {t('repository')}
          </span>
          <input type="text" value={localRepo} onChange={e => setLocalRepo(e.target.value)}
            style={inputStyle} placeholder="Agent-X-Lab"
            onFocus={e => { e.currentTarget.style.borderColor = 'var(--text-primary)'; }}
            onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-default)'; }}
          />
        </label>
        <label className="block" style={{ marginBottom: 'var(--space-lg)' }}>
          <span className="block" style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginBottom: 'var(--space-xs)' }}>
            {t('pollInterval')}
          </span>
          <select value={settings.pollInterval} onChange={e => onUpdateSettings({ pollInterval: parseInt(e.target.value) })}
            style={{ ...inputStyle, cursor: 'pointer' }}>
            <option value="15">15s</option>
            <option value="30">30s</option>
            <option value="60">60s</option>
            <option value="120">120s</option>
          </select>
        </label>

        <div className="flex gap-2" style={{ marginBottom: 'var(--space-lg)' }}>
          <button onClick={handleSave} className="axl-surface" style={{ fontSize: 14, padding: '10px 24px', borderRadius: 999, fontWeight: 600, cursor: 'pointer' }}>
            {t('save')}
          </button>
          <button onClick={handleTest} disabled={testing} className="axl-surface" style={{ fontSize: 14, padding: '10px 24px', borderRadius: 999, fontWeight: 400, cursor: 'pointer' }}>
            {testing ? t('testing') : t('test')}
          </button>
        </div>

        {testResult !== null && (
          <div style={{ fontSize: 14, color: testResult ? 'var(--text-primary)' : 'var(--signal-fail)', fontWeight: 400 }}>
            {testResult ? t('connectionOk') : t('connectionFailed')}
          </div>
        )}
        {lastVerified && (
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 400, marginTop: 'var(--space-xs)' }}>
            {t('lastVerified')} {lastVerified}
          </div>
        )}
      </div>

      <div className="axl-panel" style={{ padding: 'var(--space-lg)' }}>
        <button onClick={onClearSettings} style={{
          fontSize: 12, padding: '8px 16px', background: 'transparent',
          color: 'var(--signal-fail)', border: '1px solid var(--signal-fail)',
          cursor: 'pointer', borderRadius: 999, fontWeight: 400,
          transition: 'opacity 200ms ease-out',
        }}>
          {t('disconnect')}
        </button>
      </div>
    </div>
  );
}
