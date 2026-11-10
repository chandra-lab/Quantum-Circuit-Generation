type HistogramProps = {
  counts: Record<string, number>;
};

export function Histogram({ counts }: HistogramProps) {
  const entries = Object.entries(counts).sort(([left], [right]) => left.localeCompare(right));
  const max = Math.max(...entries.map(([, count]) => count), 1);
  const width = Math.max(320, entries.length * 64);
  const height = 190;
  const slot = (width - 24) / Math.max(entries.length, 1);
  const barWidth = Math.min(28, slot - 16);

  return (
    <div className="overflow-x-auto">
      <svg
        role="img"
        aria-label="Measurement histogram"
        viewBox={`0 0 ${width} ${height}`}
        className="h-48 min-w-full"
      >
        {entries.map(([bit, count], index) => {
          const barHeight = (count / max) * 120;
          const x = 16 + index * slot + (slot - barWidth) / 2;
          const y = 140 - barHeight;
          return (
            <g key={bit}>
              <rect data-testid={`bar-${bit}`} x={x} y={y} width={barWidth} height={barHeight} rx={3} fill="#1e3a5f" />
              <text x={x + barWidth / 2} y={y - 6} textAnchor="middle" fontSize="11" fill="#1c2430">
                {count}
              </text>
              <text x={x + barWidth / 2} y={164} textAnchor="middle" fontSize="11" fill="#1c2430" fontFamily="IBM Plex Mono, monospace">
                {bit}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
