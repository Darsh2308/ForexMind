function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono text-xs tracking-wide text-ink-faint uppercase">
        {label}
      </span>
      <span className="font-mono text-lg font-semibold text-ink tabular-nums">
        {value}
      </span>
    </div>
  )
}

// `null` from a live /api/analyze call, `undefined` when the same field was
// omitted from a stored MarketContext (the backend dumps it with
// exclude_none=True before persisting) - both mean "not set."
const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toFixed(5))

export function PriceLevels({
  entry,
  stopLoss,
  takeProfit,
  rewardToRisk,
}: {
  entry: number | null | undefined
  stopLoss: number | null | undefined
  takeProfit: number | null | undefined
  rewardToRisk: number | null | undefined
}) {
  if (entry == null && stopLoss == null && takeProfit == null) return null

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <Stat label="Entry" value={fmt(entry)} />
      <Stat label="Stop loss" value={fmt(stopLoss)} />
      <Stat label="Take profit" value={fmt(takeProfit)} />
      <Stat
        label="Reward : risk"
        value={rewardToRisk == null ? '—' : `${rewardToRisk.toFixed(2)}R`}
      />
    </div>
  )
}
