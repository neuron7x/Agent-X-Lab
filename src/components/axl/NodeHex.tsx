import type { GateStatus } from '@/lib/types';

interface OrbitalNodeProps {
  role: string;
  label: string;
  status: GateStatus;
  isActive?: boolean;
  size?: number;
  isCentral?: boolean;
}

export function NodeHex({ role, label, status, isActive, size = 104 }: OrbitalNodeProps) {
  const isFail = status === 'FAIL';
  const isAssumed = status === 'ASSUMED';
  const isRunning = status === 'RUNNING';
  const isPending = status === 'PENDING';

  const stroke = (isFail || isAssumed) ? 'var(--signal-fail)' : 'var(--text-primary)';
  const fill = isActive ? 'var(--bg-tertiary)' : 'var(--bg-secondary)';
  const textColor = isActive ? 'var(--text-primary)' : 'var(--text-secondary)';
  const opacity = isPending ? 0.35 : 1;

  const r = size / 2;
  const svgSize = size + 4;
  const center = svgSize / 2;

  // Split role into lines at semantic boundaries
  const words = role.split(/[\s-]+/);
  let lines: string[];
  if (words.length <= 1 || role.length <= 8) {
    lines = [role.toUpperCase()];
  } else {
    // Balance lines: split into 2 lines with ≤20% length variance
    const mid = Math.ceil(words.length / 2);
    const line1 = words.slice(0, mid).join(' ').toUpperCase();
    const line2 = words.slice(mid).join(' ').toUpperCase();
    lines = [line1, line2];
  }

  const lineHeight = 20;
  const totalTextHeight = lines.length * lineHeight;
  const textStartY = center - totalTextHeight / 2 + lineHeight / 2;

  return (
    <div
      className="flex flex-col items-center"
      style={{ width: svgSize + 8, transition: 'transform 200ms ease-out' }}
      role="img"
      aria-label={`${role}: ${status}`}
    >
      <svg width={svgSize} height={svgSize} viewBox={`0 0 ${svgSize} ${svgSize}`}>
        {/* Fill circle */}
        <circle
          cx={center}
          cy={center}
          r={r - 1}
          fill={fill}
          stroke="none"
          opacity={opacity}
        />

        {/* Anti-bleed inset ring — isolates text from outer stroke */}
        <circle
          cx={center}
          cy={center}
          r={r - 1.5}
          fill="none"
          stroke="var(--bg-primary)"
          strokeWidth={2}
          opacity={opacity}
        />

        {/* Outer stroke — separate layer */}
        <circle
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth={1}
          opacity={opacity}
          style={{
            animation: isRunning ? 'running-border 2s ease-in-out infinite' : undefined,
          }}
        />

        {/* Role text — optically centered with safe zone */}
        {lines.map((line, i) => (
          <text
            key={i}
            x={center}
            y={textStartY + i * lineHeight}
            textAnchor="middle"
            dominantBaseline="central"
            fill={textColor}
            fontSize={15}
            fontFamily="'Inter', system-ui, sans-serif"
            fontWeight={600}
            opacity={opacity}
            letterSpacing="0.015em"
          >
            {line}
          </text>
        ))}
      </svg>

      {/* Label below */}
      <span
        style={{
          fontSize: 12,
          color: 'var(--text-tertiary)',
          fontWeight: 400,
          marginTop: 8,
          letterSpacing: '0.01em',
          textAlign: 'center',
          lineHeight: '16px',
        }}
      >
        {label}
      </span>
    </div>
  );
}
