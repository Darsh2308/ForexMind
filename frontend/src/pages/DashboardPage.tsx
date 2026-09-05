import { useMemo } from 'react'
import { ApiError } from '../api/client'
import { AnalyzeProgress } from '../components/AnalyzeProgress'
import { ChatPanel } from '../components/ChatPanel'
import { KpiCard } from '../components/KpiCard'
import { LiveChart } from '../components/LiveChart'
import { RecentActivity } from '../components/RecentActivity'
import { RecommendationResult } from '../components/RecommendationResult'
import { useAnalyze } from '../hooks/useAnalyze'
import { useHealth } from '../hooks/useHealth'
import { useHistory } from '../hooks/useHistory'
import { useLiveCandles } from '../hooks/useLiveCandles'
import { useSimulatedProgress } from '../hooks/useSimulatedProgress'

// Fetched with a higher limit than the History page's default (50) so the
// KPI counts below aren't silently truncated once real usage grows.
const KPI_HISTORY_LIMIT = 200

export function DashboardPage() {
  const analyze = useAnalyze()
  const currentStep = useSimulatedProgress(analyze.isPending)
  const health = useHealth()
  const history = useHistory(KPI_HISTORY_LIMIT)
  const liveCandles = useLiveCandles('15min')

  const kpis = useMemo(() => {
    const items = history.data?.recommendations ?? []
    const resolved = items.filter((i) => i.status === 'WIN' || i.status === 'LOSS')
    const wins = resolved.filter((i) => i.status === 'WIN').length
    return {
      total: items.length,
      winRate:
        resolved.length > 0 ? `${Math.round((wins / resolved.length) * 100)}%` : '—',
      open: items.filter((i) => i.status === 'PENDING').length,
    }
  }, [history.data])

  const latestPrice = history.isSuccess
    ? liveCandles.data?.candles.at(-1)?.close
    : undefined
  const backendOk = health.data?.status === 'ok'
  const backendTone = health.isLoading ? 'neutral' : backendOk ? 'buy' : 'sell'

  // Seed chat with the newest recommendation if we already have one; null is
  // fine too (e.g. history hasn't loaded yet, or there's no history at all)
  // since /api/chat's "cold chat" mode grounds itself in that case, running
  // a fresh analysis first if the latest call is missing or stale.
  const latestRecommendationId = history.data?.recommendations[0]?.id ?? null

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-balance">
          Should I buy EUR/USD right now?
        </h1>
        <p className="mt-2 max-w-prose text-ink-soft">
          Fourteen agents investigate market structure, price action, indicators, news and
          history before answering &mdash; not a signal, a case.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <KpiCard
          label="Live price"
          value={latestPrice !== undefined ? latestPrice.toFixed(5) : '—'}
        />
        <KpiCard
          label="Backend"
          value={health.isLoading ? '…' : backendOk ? 'OK' : 'Down'}
          tone={backendTone}
        />
        <KpiCard label="Recommendations" value={String(kpis.total)} />
        <KpiCard label="Win rate" value={kpis.winRate} subLabel="resolved calls only" />
        <KpiCard label="Open" value={String(kpis.open)} subLabel="pending" />
      </div>

      <LiveChart interval="15min" />

      <div className="flex flex-col items-start gap-4">
        <button
          type="button"
          onClick={() => analyze.mutate('EUR/USD')}
          disabled={analyze.isPending}
          className="w-fit rounded-md bg-accent px-5 py-2.5 font-medium text-accent-contrast transition-opacity disabled:cursor-not-allowed disabled:opacity-60"
        >
          {analyze.isPending
            ? 'Investigating…'
            : analyze.isError || analyze.isSuccess
              ? 'Analyze again'
              : 'Analyze EUR/USD now'}
        </button>

        {analyze.isPending && (
          <div className="w-full max-w-sm rounded-lg border border-line bg-raised p-4">
            <AnalyzeProgress currentStep={currentStep} />
          </div>
        )}

        {analyze.isError && (
          <div className="rounded-md bg-sell-soft px-3 py-2.5 text-sm text-sell">
            <p className="font-medium">Couldn&rsquo;t get a recommendation.</p>
            <p className="mt-0.5">
              {analyze.error instanceof ApiError
                ? analyze.error.message
                : 'Something unexpected went wrong.'}
            </p>
          </div>
        )}
      </div>

      {analyze.isSuccess && <RecommendationResult result={analyze.data} />}

      <RecentActivity items={history.data?.recommendations ?? []} />

      <ChatPanel recommendationId={latestRecommendationId} />
    </div>
  )
}
