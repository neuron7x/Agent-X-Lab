import type { VRData, Gate, ConnectionStatus } from '@/lib/types';
import { useLanguage } from '@/hooks/useLanguage';

interface ErrorBannerProps {
  vrData: VRData | null;
  gates: Gate[];
  connectionStatus: ConnectionStatus;
  error: string | null;
  rateLimitReset: number | null;
  contractError?: string | null;
}

export function ErrorBanner({ vrData, gates, connectionStatus, error, rateLimitReset, contractError }: ErrorBannerProps) {
  const { t } = useLanguage();
  const failedGates = gates.filter(g => g.status === 'FAIL');

  const bannerStyle = (color: string): React.CSSProperties => ({
    position: 'fixed', top: 48, left: 0, right: 0, zIndex: 40,
    padding: '8px var(--space-xl)',
    background: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border-default)',
    fontSize: 12, color, fontWeight: 400,
  });

  if (contractError) {
    return <div style={bannerStyle('var(--signal-fail)')}>⚠ {contractError}</div>;
  }

  if (connectionStatus === 'RATE_LIMITED' && rateLimitReset) {
    const resetDate = new Date(rateLimitReset * 1000);
    return <div style={bannerStyle('var(--signal-warn)')}>{t('rateLimitedResets')} {resetDate.toISOString().slice(11, 19)}Z</div>;
  }

  if (connectionStatus === 'ERROR' && error) {
    return <div style={bannerStyle('var(--signal-fail)')}>{t('errorDash')} {error}</div>;
  }

  if (failedGates.length > 0) {
    return <div style={{ ...bannerStyle('var(--signal-fail)'), fontWeight: 500 }}>{t('failDash')} {failedGates.map(g => g.id).join(', ')}</div>;
  }

  if (vrData && vrData.status !== 'RUN') {
    const blockersCount = Array.isArray(vrData.blockers) ? vrData.blockers.length : 0;
    return <div style={bannerStyle('var(--signal-warn)')}>{t('statusColon')} {vrData.status}{blockersCount > 0 ? ` — ${t('blockersColon')} ${blockersCount}` : ''}</div>;
  }

  return null;
}
