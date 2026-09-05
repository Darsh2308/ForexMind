export function KpiCard({
  label,
  value,
  subLabel,
  tone = 'neutral',
}: {
  label: string
  value: string
  subLabel?: string
  tone?: 'neutral' | 'buy' | 'sell'
}) {
  const valueClass =
    tone === 'buy' ? 'text-buy' : tone === 'sell' ? 'text-sell' : 'text-ink'

  return (
    <div className="flex flex-col gap-1 rounded-lg border border-line bg-raised p-4">
      <span className="font-mono text-xs tracking-wide text-ink-faint uppercase">
        {label}
      </span>
      <span className={`font-mono text-2xl font-semibold tabular-nums ${valueClass}`}>
        {value}
      </span>
      {subLabel && <span className="text-xs text-ink-faint">{subLabel}</span>}
    </div>
  )
}
