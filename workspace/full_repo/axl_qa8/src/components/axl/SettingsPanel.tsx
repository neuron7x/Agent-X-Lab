/**
 * SettingsPanel — NO token field.
 * Auth is entirely server-side in the BFF Worker.
 */
import { useState } from 'react';
import type { GitHubSettings } from '@/lib/types';
import { healthz } from '@/lib/api';
import { useLanguage } from '@/hooks/useLanguage';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  settings: GitHubSettings;
  onUpdateSettings: (patch: Partial<Omit<GitHubSettings, 'token'>>) => void;
  onClearSettings: () => void;
  lastVerified: string | null;
  isDemoMode?: boolean;
  onExitDemo?: () => void;
}

export function SettingsPanel({
  isOpen, onClose, settings, onUpdateSettings, onClearSettings,
  lastVerified, isDemoMode, onExitDemo,
}: SettingsPanelProps) {
  const { t } = useLanguage();
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

  if (!isOpen) return null;

  const inputStyle: React.CSSProperties = {
    background: 'var(--bg-void)',
    border: '1px solid var(--border-dim)',
    color: 'var(--text-primary)',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    padding: '8px 12px',
    width: '100%',
    borderRadius: '2px',
    outline: 'none',
  };

  const bffBase = (import.meta.env?.VITE_AXL_API_BASE as string | undefined) ?? '(not set)';

  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 60 }} />
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 380, zIndex: 70,
        background: 'var(--bg-surface)',
        borderLeft: '1px solid var(--border-dim)',
        animation: 'slide-in-right 0.2s ease-out',
        overflowY: 'auto',
        padding: '24px 20px',
      }}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="axl-label" style={{ fontSize: '12px' }}>{t('settings')}</h2>
          <button onClick={onClose} className="font-mono"
            style={{ color: 'var(--text-secondary)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '14px' }}>
            ✕
          </button>
        </div>

        {/* BFF endpoint (read-only — configured via env var) */}
        <section className="mb-4">
          <h3 className="axl-label mb-2" style={{ fontSize: '10px' }}>BFF ENDPOINT</h3>
          <div className="font-mono" style={{
            fontSize: '10px', padding: '6px 10px',
            background: 'var(--bg-elevated)', border: '1px solid var(--border-dim)',
            borderRadius: '2px', color: 'var(--text-secondary)',
            wordBreak: 'break-all',
          }}>
            {bffBase}
          </div>
          <p style={{ fontSize: '9px', color: 'var(--text-dim)', marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>
            Set via VITE_AXL_API_BASE env var. No token stored in browser.
          </p>
        </section>

        <div className="axl-divider" />

        <section className="mb-6 mt-4">
          <h3 className="axl-label mb-3" style={{ fontSize: '10px' }}>{t('githubIntegration')}</h3>

          <label className="block mb-3">
            <span className="axl-label block mb-1" style={{ fontSize: '9px' }}>{t('owner')}</span>
            <input type="text" value={localOwner} onChange={e => setLocalOwner(e.target.value)}
              style={inputStyle} placeholder="username" />
          </label>

          <label className="block mb-3">
            <span className="axl-label block mb-1" style={{ fontSize: '9px' }}>{t('repository')}</span>
            <input type="text" value={localRepo} onChange={e => setLocalRepo(e.target.value)}
              style={inputStyle} placeholder="Agent-X-Lab" />
          </label>

          <label className="block mb-4">
            <span className="axl-label block mb-1" style={{ fontSize: '9px' }}>{t('pollInterval')}</span>
            <select
              value={settings.pollInterval}
              onChange={e => onUpdateSettings({ pollInterval: parseInt(e.target.value) })}
              style={{ ...inputStyle, cursor: 'pointer' }}
            >
              <option value="15">15s</option>
              <option value="30">30s</option>
              <option value="60">60s</option>
              <option value="120">120s</option>
            </select>
          </label>

          <div className="flex gap-2 mb-4">
            <button onClick={handleSave} className="font-mono" style={{
              fontSize: '11px', padding: '6px 16px', background: '#00e87a15', color: '#00e87a',
              border: '1px solid #00e87a40', cursor: 'pointer', borderRadius: '2px', letterSpacing: '0.06em',
            }}>{t('save')}</button>
            <button onClick={handleTest} disabled={testing} className="font-mono" style={{
              fontSize: '11px', padding: '6px 16px', background: 'var(--bg-elevated)', color: 'var(--text-secondary)',
              border: '1px solid var(--border-dim)', cursor: 'pointer', borderRadius: '2px', letterSpacing: '0.06em',
            }}>{testing ? t('testing') : t('test')}</button>
          </div>

          {testResult !== null && (
            <div className="font-mono" style={{ fontSize: '10px', color: testResult ? '#00e87a' : '#ff2d55' }}>
              {testResult ? t('connectionOk') : t('connectionFailed')}
            </div>
          )}
          {lastVerified && (
            <div className="font-mono mt-1" style={{ fontSize: '9px', color: 'var(--text-dim)' }}>
              {t('lastVerified')} {lastVerified}
            </div>
          )}
        </section>

        <div className="axl-divider" />

        <section className="mt-4 flex flex-col gap-3">
          {isDemoMode && onExitDemo && (
            <button onClick={() => { onExitDemo(); onClose(); }} className="font-mono" style={{
              fontSize: '10px', padding: '4px 12px', background: '#ffaa0010', color: '#ffaa00',
              border: '1px solid #ffaa0030', cursor: 'pointer', borderRadius: '2px', letterSpacing: '0.06em',
            }}>{t('exitDemo')}</button>
          )}
          <button onClick={onClearSettings} className="font-mono" style={{
            fontSize: '10px', padding: '4px 12px', background: '#ff2d5510', color: '#ff2d55',
            border: '1px solid #ff2d5530', cursor: 'pointer', borderRadius: '2px', letterSpacing: '0.06em',
          }}>{t('disconnect')}</button>
        </section>
      </div>
    </>
  );
}
