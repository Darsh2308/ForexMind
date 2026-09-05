import { useCandles } from '../hooks/useCandles'
import type { MarketContext, ReasoningSnapshot } from '../types/api'
import { PriceChart } from './PriceChart'
import { Skeleton } from './Skeleton'

/** Session shading (per Development.md Phase 5) is scoped down to a plain
 * caption here: lightweight-charts has no built-in time-of-day shading
 * primitive, and building one is out of proportion to what this line needs
 * to communicate. */
function ActiveSessions({ marketContext }: { marketContext: MarketContext }) {
  const sessions = (marketContext.market_data?.sessions as { active_sessions?: string[] })
    ?.active_sessions
  if (!sessions || sessions.length === 0) return null

  return (
    <p className="font-mono text-xs text-ink-faint">
      Active session{sessions.length > 1 ? 's' : ''} at analysis time:{' '}
      {sessions.join(', ')}
    </p>
  )
}

export function RecommendationChart({
  createdAt,
  marketContext,
  reasoning,
}: {
  createdAt: string
  marketContext: MarketContext
  reasoning: ReasoningSnapshot | null | undefined
}) {
  const interval = marketContext.timeframes?.[0] ?? '15min'
  const candles = useCandles(interval, createdAt)

  if (candles.isLoading) {
    return <Skeleton className="h-80 w-full rounded-lg" />
  }
  if (candles.isError || !candles.data || candles.data.candles.length === 0) {
    return null
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-line bg-raised p-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-mono text-xs font-medium tracking-wide text-ink-faint uppercase">
          Price chart &mdash; {interval}
        </h2>
        <ActiveSessions marketContext={marketContext} />
      </div>
      <PriceChart
        candles={candles.data.candles}
        entry={reasoning?.entry}
        stopLoss={reasoning?.stop_loss}
        takeProfit={reasoning?.take_profit}
      />
    </div>
  )
}
