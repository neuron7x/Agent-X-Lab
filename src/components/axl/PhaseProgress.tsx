const PHASES = [
  { id: 0, label: 'BASELINE' },
  { id: 1, label: 'SECURITY' },
  { id: 2, label: 'RELEASE' },
  { id: 3, label: 'OPS' },
  { id: 4, label: 'CANARY' },
  { id: 5, label: 'LAUNCH' },
];

interface PhaseProgressProps {
  currentPhase: number; // 0-5
}

export function PhaseProgress({ currentPhase }: PhaseProgressProps) {
  return (
    <div className="flex items-center justify-center gap-0 py-3 px-4">
      {PHASES.map((phase, i) => {
        const completed = i < currentPhase;
        const active = i === currentPhase;
        const future = i > currentPhase;

        return (
          <div key={phase.id} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <div
                className="flex items-center justify-center"
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: completed ? '#00e87a' : 'transparent',
                  border: future ? '1.5px solid #333348' : active ? '1.5px solid #00e87a' : 'none',
                  animation: active ? 'glow-pulse 2s ease-in-out infinite' : undefined,
                  boxShadow: active ? '0 0 8px #00e87a60' : undefined,
                }}
                aria-label={`Phase ${phase.id}: ${phase.label} — ${completed ? 'completed' : active ? 'active' : 'pending'}`}
              />
              <span
                className="font-mono"
                style={{
                  fontSize: '8px',
                  color: completed ? '#00e87a' : active ? 'var(--text-primary)' : 'var(--text-dim)',
                  letterSpacing: '0.06em',
                  fontWeight: active ? 500 : 400,
                }}
              >
                {phase.label}
              </span>
            </div>
            {i < PHASES.length - 1 && (
              <div
                style={{
                  width: 32,
                  height: 1,
                  background: completed ? '#00e87a40' : 'var(--border-dim)',
                  margin: '0 4px',
                  marginBottom: '14px',
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
