import type { VRData, Gate } from '@/lib/types';
import { useLanguage } from '@/hooks/useLanguage';
import { useState, useCallback, useRef } from 'react';

interface HomeScreenProps {
  vrData: VRData | null;
  gates: Gate[];
  onViewPipeline: () => void;
  onNavigateToArsenal: () => void;
  contractError?: string | null;
}

export function HomeScreen({ vrData, gates, onViewPipeline, onNavigateToArsenal, contractError }: HomeScreenProps) {
  const { t } = useLanguage();
  const rawStatus = vrData?.status || '—';
  const isRun = rawStatus === 'RUN';
  const isFail = rawStatus === 'FAIL';

  const passRate = vrData?.metrics?.pass_rate != null
    ? (Number(vrData.metrics.pass_rate) * 100).toFixed(1)
    : '—';
  const blockers = vrData ? (Array.isArray(vrData.blockers) ? vrData.blockers.length : 0) : 0;
  const totalGates = gates.length;
  const passedGates = gates.filter(g => g.status === 'PASS' || g.status === 'ASSUMED').length;

  const determinism = vrData?.metrics?.determinism as string | undefined;
  const determinismOk = vrData?.metrics?.determinism_ok;
  const isDeterminismAssumed = determinism === 'ASSUMED_SINGLE_RUN' || determinismOk === false || (!determinism && vrData != null);

  const borderColor = isRun ? '#ffffff' : isFail ? '#ff2d55' : '#1c1c1c';

  const [btnHover, setBtnHover] = useState(false);
  const [circleHover, setCircleHover] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const [animPhase, setAnimPhase] = useState<0 | 1 | 2>(0);
  const timerRef = useRef<number>(0);

  const handleCircleClick = useCallback(() => {
    if (isAnimating) return;
    setIsAnimating(true);
    setAnimPhase(1);

    timerRef.current = window.setTimeout(() => {
      setAnimPhase(2);

      timerRef.current = window.setTimeout(() => {
        onNavigateToArsenal();
        setIsAnimating(false);
        setAnimPhase(0);
      }, 200);
    }, 150);
  }, [isAnimating, onNavigateToArsenal]);

  const circleScale = animPhase === 1 ? 1.08 : animPhase === 2 ? 0 : circleHover ? 1.02 : 1;
  const circleTransition = animPhase === 2
    ? 'transform 200ms ease-in, border-color 200ms'
    : animPhase === 1
      ? 'transform 150ms ease-out, border-color 200ms'
      : 'transform 200ms ease, border-color 200ms';
  const contentOpacity = animPhase === 2 ? 0 : 1;
  const textOpacity = animPhase >= 1 ? 0 : 1;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 'calc(100vh - 48px)',
        paddingTop: 48,
        paddingBottom: 48,
        opacity: contentOpacity,
        transition: animPhase === 2 ? 'opacity 200ms ease-in' : undefined,
      }}
    >
      {contractError && (
        <div style={{
          fontSize: 10,
          fontFamily: 'JetBrains Mono, monospace',
          color: '#ff2d55',
          border: '1px solid #ff2d55',
          padding: '2px 12px',
          borderRadius: 2,
          fontWeight: 400,
          marginBottom: 24,
          letterSpacing: '0.06em',
        }}>
          ⚠ {contractError}
        </div>
      )}

      {/* CIRCLE */}
      <div style={{ position: 'relative' }}>
        <div
          onClick={handleCircleClick}
          onMouseEnter={() => setCircleHover(true)}
          onMouseLeave={() => setCircleHover(false)}
          style={{
            width: 200,
            height: 200,
            borderRadius: '50%',
            border: `1px solid ${circleHover || isAnimating ? '#ffffff' : borderColor}`,
            background: '#000',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            cursor: 'pointer',
            transform: `scale(${circleScale})`,
            transition: circleTransition,
          }}
          aria-label={`${t('vrStatus')}: ${rawStatus}`}
        >
          <span style={{
            fontSize: 32,
            fontWeight: 700,
            color: '#ffffff',
            letterSpacing: '0.15em',
            fontFamily: 'JetBrains Mono, monospace',
            lineHeight: 1,
            opacity: textOpacity,
            transition: 'opacity 100ms ease',
          }}>
            {rawStatus}
          </span>
        </div>

        {/* TOOLTIP */}
        <div style={{
          position: 'absolute',
          left: '50%',
          transform: 'translateX(-50%)',
          top: 'calc(100% + 10px)',
          fontSize: 10,
          fontFamily: 'JetBrains Mono, monospace',
          color: '#444444',
          whiteSpace: 'nowrap',
          opacity: circleHover && !isAnimating ? 1 : 0,
          transition: 'opacity 200ms ease',
          pointerEvents: 'none',
          letterSpacing: '0.06em',
        }}>
          {t('clickToArsenal')}
        </div>
      </div>

      {/* GAP: circle → metrics = 48px */}
      <div style={{ height: 48, flexShrink: 0 }} />

      {/* METRICS ROW */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 48 }}>
        <Metric label={t('passRate')} value={`${passRate}%`} />
        <div style={{ width: 1, height: 32, background: '#1c1c1c', flexShrink: 0 }} />
        <Metric label={t('blockers')} value={String(blockers)} warn={blockers > 0} />
        <div style={{ width: 1, height: 32, background: '#1c1c1c', flexShrink: 0 }} />
        <Metric label={t('gates')} value={`${passedGates}/${totalGates}`} />
      </div>

      {/* DETERMINISM PILL */}
      {isDeterminismAssumed && (
        <>
          <div style={{ height: 24, flexShrink: 0 }} />
          <div style={{
            fontSize: 10,
            fontFamily: 'JetBrains Mono, monospace',
            color: '#ff3b30',
            border: '1px solid #ff3b30',
            background: '#ff3b3008',
            padding: '2px 12px',
            borderRadius: 2,
            fontWeight: 400,
            letterSpacing: '0.06em',
            lineHeight: 1.4,
          }}>
            {t('assumedSingleRun')}
          </div>
        </>
      )}

      {/* SHA / UTC ROW */}
      {vrData && (
        <>
          <div style={{ height: isDeterminismAssumed ? 16 : 24, flexShrink: 0 }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <span style={{ fontSize: 9, color: '#444444', fontFamily: 'JetBrains Mono, monospace', fontWeight: 300 }}>
              {vrData.work_id?.slice(0, 8)}
            </span>
            <span style={{ fontSize: 9, color: '#444444', fontFamily: 'JetBrains Mono, monospace', fontWeight: 300 }}>
              {vrData.utc}
            </span>
          </div>
        </>
      )}

      {/* GAP: sha/utc → button = 40px */}
      <div style={{ height: 40, flexShrink: 0 }} />

      {/* BUTTON */}
      <button
        onClick={onViewPipeline}
        onMouseEnter={() => setBtnHover(true)}
        onMouseLeave={() => setBtnHover(false)}
        style={{
          padding: '10px 32px',
          border: `1px solid ${btnHover ? '#ffffff' : '#1c1c1c'}`,
          background: 'transparent',
          borderRadius: 2,
          fontSize: 11,
          fontFamily: 'JetBrains Mono, monospace',
          fontWeight: 500,
          color: '#ffffff',
          letterSpacing: '0.1em',
          cursor: 'pointer',
          transition: 'border-color 150ms',
        }}
      >
        {t('viewPipeline')}
      </button>
    </div>
  );
}

function Metric({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <span style={{
        fontSize: 10,
        color: '#444444',
        fontFamily: 'JetBrains Mono, monospace',
        fontWeight: 400,
        letterSpacing: '0.12em',
        marginBottom: 8,
        textTransform: 'uppercase' as const,
      }}>
        {label}
      </span>
      <span style={{
        fontSize: 20,
        color: warn ? '#ff2d55' : '#ffffff',
        fontFamily: 'JetBrains Mono, monospace',
        fontWeight: 500,
        lineHeight: 1,
      }}>
        {value}
      </span>
    </div>
  );
}
