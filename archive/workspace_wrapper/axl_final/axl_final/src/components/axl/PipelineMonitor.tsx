import type { Gate } from '@/lib/types';
import { ARALoop } from './ARALoop';
import { PhaseProgress } from './PhaseProgress';
import { GateTable } from './GateTable';

interface PipelineMonitorProps {
  gates: Gate[];
}

export function PipelineMonitor({ gates }: PipelineMonitorProps) {
  // Determine active phase from gate statuses
  const phaseGates = [
    ['G.REPO.001', 'G.REPO.002', 'G.REPO.003', 'G.DET.001', 'G.DET.002'], // BASELINE
    ['G.SEC.001', 'G.SEC.002', 'G.SEC.003'],                                 // SECURITY
    ['G.RELEASE.001', 'G.RELEASE.002', 'G.RELEASE.003'],                     // RELEASE
    ['G.OPS.001', 'G.OPS.002', 'G.OPS.003'],                                 // OPS
    ['G.CANARY.001', 'G.CANARY.002'],                                        // CANARY
    ['G.FINAL.001'],                                                          // LAUNCH
  ];

  let currentPhase = 0;
  for (let i = 0; i < phaseGates.length; i++) {
    const allPassed = phaseGates[i].every(gId => {
      const g = gates.find(gate => gate.id === gId);
      return g && (g.status === 'PASS' || g.status === 'ASSUMED');
    });
    if (allPassed) currentPhase = i + 1;
    else break;
  }

  // ARA loop phase (0-3) based on overall progress
  const araPhase = Math.min(Math.floor(currentPhase * 4 / 6), 3);

  return (
    <div className="flex flex-col gap-3 h-full" style={{ animation: 'stagger-reveal 0.3s ease-out forwards', animationDelay: '80ms' }}>
      <div className="axl-panel p-4">
        <h2 className="axl-label mb-2" style={{ fontSize: '12px' }}>ARA-LOOP VISUALIZER</h2>
        <ARALoop activePhase={araPhase} />
      </div>

      <div className="axl-panel p-3">
        <PhaseProgress currentPhase={currentPhase} />
      </div>

      <div className="flex-1 min-h-0">
        <GateTable gates={gates} />
      </div>
    </div>
  );
}
