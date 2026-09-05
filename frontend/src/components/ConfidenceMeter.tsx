import type { Recommendation } from '../types/api'

const fillClass: Record<Recommendation, string> = {
  BUY: 'bg-buy',
  SELL: 'bg-sell',
  WAIT: 'bg-wait',
}

export function ConfidenceMeter({
  confidence,
  recommendation,
}: {
  confidence: number
  recommendation: Recommendation
}) {
  const pct = Math.round(Math.max(0, Math.min(1, confidence)) * 100)

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-xs tracking-wide text-ink-faint uppercase">
          Confidence
        </span>
        <span className="font-mono text-sm font-semibold text-ink tabular-nums">
          {pct}%
        </span>
      </div>
      <div
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Confidence"
        className="h-2 w-full overflow-hidden rounded-full bg-accent-soft"
      >
        <div
          className={`h-full rounded-full ${fillClass[recommendation]} transition-[width]`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
