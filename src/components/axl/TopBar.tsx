import { useState, useEffect } from 'react';
import type { ConnectionStatus } from '@/lib/types';
import { useLanguage } from '@/hooks/useLanguage';
import type { TranslationKey } from '@/lib/i18n';

interface TopBarProps {
  repoName?: string;
  connectionStatus?: ConnectionStatus;
  demoMode?: boolean;
  onSettingsClick?: () => void;
  onOpenCommandPalette?: () => void;
  rateLimitReset?: number | null;
}

const STATUS_COLORS: Record<ConnectionStatus, string> = {
  DISCONNECTED: '#444444',
  CONNECTED: '#ffffff',
  POLLING: '#0a84ff',
  ERROR: '#ff3b30',
  RATE_LIMITED: '#ff9f0a',
};

const STATUS_KEYS: Record<ConnectionStatus, TranslationKey> = {
  CONNECTED: 'connLive',
  POLLING: 'connPolling',
  DISCONNECTED: 'connOffline',
  ERROR: 'connError',
  RATE_LIMITED: 'connRateLimited',
};

function formatCountdown(seconds: number): string {
  if (seconds <= 0) return '00:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export function TopBar({
  repoName = '—',
  connectionStatus = 'DISCONNECTED',
  demoMode = false,
  onSettingsClick,
  rateLimitReset,
}: TopBarProps) {
  const { t } = useLanguage();
  const dotColor = demoMode ? STATUS_COLORS.DISCONNECTED : STATUS_COLORS[connectionStatus];
  const statusLabel = demoMode ? t('demo') : t(STATUS_KEYS[connectionStatus]);

  const [countdown, setCountdown] = useState('');
  useEffect(() => {
    if (connectionStatus !== 'RATE_LIMITED' || !rateLimitReset) {
      setCountdown('');
      return;
    }
    const tick = () => {
      const remaining = Math.max(0, rateLimitReset - Math.floor(Date.now() / 1000));
      setCountdown(formatCountdown(remaining));
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [connectionStatus, rateLimitReset]);

  return (
    <header
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between"
      style={{ height: 48, background: 'var(--bg-primary)', borderBottom: '1px solid var(--border-default)', padding: '0 var(--space-lg)' }}
    >
      <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '0.01em' }}>AGENT-X-LAB</span>

      <div className="flex items-center gap-3">
        <span style={{ fontSize: 14, color: 'var(--text-tertiary)', fontWeight: 400 }}>{repoName}</span>
        {demoMode && (
          <span style={{ fontSize: 12, color: 'var(--text-tertiary)', border: '1px solid var(--border-default)', padding: '2px 8px', borderRadius: 999, fontWeight: 400 }}>
            {t('demo')}
          </span>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2" aria-label={`${t('connectionLabel')}: ${statusLabel}`}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: dotColor, animation: !demoMode && connectionStatus === 'POLLING' ? 'connection-pulse 2s ease-in-out infinite' : undefined }} />
          <span style={{ fontSize: 12, color: dotColor, fontWeight: 400 }}>
            {statusLabel}
            {connectionStatus === 'RATE_LIMITED' && countdown ? ` ${countdown}` : ''}
          </span>
        </div>
        <button
          onClick={onSettingsClick}
          className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, minWidth: 48, minHeight: 48, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          aria-label={t('settings')}
        >⚙</button>
      </div>
    </header>
  );
}
