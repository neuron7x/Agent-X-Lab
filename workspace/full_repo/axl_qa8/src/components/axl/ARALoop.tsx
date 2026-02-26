import { NodeHex } from './NodeHex';
import type { GateStatus } from '@/lib/types';
import { useLanguage } from '@/hooks/useLanguage';
import type { TranslationKey } from '@/lib/i18n';

interface ARALoopProps {
  activePhase: number;
}

const NODES: { roleKey: TranslationKey; labelKey: TranslationKey }[] = [
  { roleKey: 'nodePreLogic', labelKey: 'labelThinking' },
  { roleKey: 'nodeExecutor', labelKey: 'labelCodex' },
  { roleKey: 'nodeAraLoop', labelKey: 'labelCiLogs' },
  { roleKey: 'nodeAuditor', labelKey: 'labelPostAudit' },
];

const NODE_SIZE = 104;
const CONNECTOR_GAP = 96;

export function ARALoop({ activePhase }: ARALoopProps) {
  const { t } = useLanguage();

  const nodes = NODES.map((node, i) => {
    let status: GateStatus = 'PENDING';
    if (i < activePhase) status = 'PASS';
    else if (i === activePhase) status = 'RUNNING';
    return { ...node, status, isActive: i === activePhase, isCentral: i === 0 };
  });

  return (
    <div className="flex flex-col items-center py-4" style={{ width: '100%', overflowX: 'auto' }}>
      <div className="flex items-start justify-center">
        {nodes.map((node, i) => {
          const isPast = i > 0 && i <= activePhase;
          const isCurrent = i > 0 && i === activePhase;

          return (
            <div key={node.roleKey} className="flex items-center" style={{ flexShrink: 0 }}>
              {/* Connector — terminates at circle perimeter */}
              {i > 0 && (
                <svg
                  width={CONNECTOR_GAP}
                  height="12"
                  viewBox={`0 0 ${CONNECTOR_GAP} 12`}
                  aria-hidden="true"
                  style={{ display: 'block', marginTop: -(NODE_SIZE * 0.12) }}
                >
                  <line
                    x1="0"
                    y1="6"
                    x2={CONNECTOR_GAP - 8}
                    y2="6"
                    stroke={isPast ? 'var(--text-secondary)' : 'var(--border-default)'}
                    strokeWidth={1}
                    opacity={isPast ? 0.6 : 0.3}
                    strokeDasharray={isPast ? 'none' : '4 4'}
                    style={{
                      animation: isCurrent && !isPast
                        ? 'flow-dash 0.8s linear infinite'
                        : undefined,
                    }}
                  />
                  <polygon
                    points={`${CONNECTOR_GAP - 8},3 ${CONNECTOR_GAP},6 ${CONNECTOR_GAP - 8},9`}
                    fill={isPast ? 'var(--text-secondary)' : 'var(--border-default)'}
                    opacity={isPast ? 0.6 : 0.3}
                  />
                </svg>
              )}
              <NodeHex
                role={t(node.roleKey)}
                label={t(node.labelKey)}
                status={node.status}
                isActive={node.isActive}
                size={NODE_SIZE}
                isCentral={node.isCentral}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
