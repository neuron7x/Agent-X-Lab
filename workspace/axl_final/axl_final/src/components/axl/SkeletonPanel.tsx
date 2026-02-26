interface SkeletonPanelProps {
  lines?: number;
}

export function SkeletonPanel({ lines = 4 }: SkeletonPanelProps) {
  return (
    <div className="axl-panel" style={{ padding: 'var(--space-lg)' }}>
      <div className="flex flex-col" style={{ gap: 'var(--space-md)' }}>
        {Array.from({ length: lines }, (_, i) => (
          <div
            key={i}
            className="animate-pulse"
            style={{
              height: 8,
              background: 'var(--border-default)',
              borderRadius: 4,
              width: `${70 - i * 10}%`,
              opacity: 0.3,
            }}
          />
        ))}
      </div>
    </div>
  );
}
