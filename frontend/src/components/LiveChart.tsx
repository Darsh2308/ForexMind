import { useLiveCandles } from '../hooks/useLiveCandles'
import { PriceChart } from './PriceChart'
import { Skeleton } from './Skeleton'

export function LiveChart({ interval = '15min' }: { interval?: string }) {
  const candles = useLiveCandles(interval)

  if (candles.isLoading) {
    return <Skeleton className="h-80 w-full rounded-lg" />
  }
  if (candles.isError || !candles.data || candles.data.candles.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-line p-8 text-center text-sm text-ink-faint">
        No candle data available yet &mdash; run a backfill first.
      </div>
    )
  }

  const latest = candles.data.candles[candles.data.candles.length - 1]

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-line bg-raised p-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-mono text-xs font-medium tracking-wide text-ink-faint uppercase">
          EUR/USD &mdash; {interval}
        </h2>
        <span className="font-mono text-xs text-ink-faint">
          Latest stored candle: {latest?.timestamp} UTC
        </span>
      </div>
      <PriceChart candles={candles.data.candles} />
    </div>
  )
}
