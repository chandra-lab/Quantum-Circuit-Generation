type ProbabilityBarsProps = {
  probabilities: Record<string, number>;
};

export function ProbabilityBars({ probabilities }: ProbabilityBarsProps) {
  const entries = Object.entries(probabilities).sort(([left], [right]) => left.localeCompare(right));
  return (
    <ul className="space-y-3">
      {entries.map(([bit, probability]) => {
        const percent = Math.max(0, Math.min(100, probability * 100));
        return (
          <li key={bit}>
            <div className="mb-1 flex items-baseline justify-between gap-3 font-mono text-xs">
              <span>{bit}</span>
              <span>{percent.toFixed(1)}%</span>
            </div>
            <div className="h-2 rounded-full bg-line" aria-hidden="true">
              <div className="h-2 rounded-full bg-copper" style={{ width: `${percent}%` }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
