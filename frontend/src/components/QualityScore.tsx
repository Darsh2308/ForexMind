/** ReasoningSnapshot.trade_quality_score is 1-10 (see reasoning/schemas.py). */
export function QualityScore({ score }: { score: number }) {
  const clamped = Math.max(1, Math.min(10, Math.round(score)))

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-xs tracking-wide text-ink-faint uppercase">
          Trade quality
        </span>
        <span className="font-mono text-sm font-semibold text-ink tabular-nums">
          {clamped}/10
        </span>
      </div>
      <div
        className="flex gap-1"
        role="img"
        aria-label={`Trade quality ${clamped} out of 10`}
      >
        {Array.from({ length: 10 }, (_, i) => (
          <span
            key={i}
            className={`h-2 flex-1 rounded-sm ${i < clamped ? 'bg-accent' : 'bg-accent-soft'}`}
          />
        ))}
      </div>
    </div>
  )
}
