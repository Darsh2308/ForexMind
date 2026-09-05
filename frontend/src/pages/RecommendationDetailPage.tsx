import { useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { AgentSectionPanel } from '../components/AgentSectionPanel'
import { ChatPanel } from '../components/ChatPanel'
import { RecommendationChart } from '../components/RecommendationChart'
import { RecommendationResult } from '../components/RecommendationResult'
import { Skeleton } from '../components/Skeleton'
import { OutcomeChip } from '../components/StatusChip'
import { useRecommendationDetail } from '../hooks/useRecommendationDetail'
import type { MarketContext, MarketContextSection } from '../types/api'

// Reading order roughly follows the pipeline itself (orchestration/graph.py):
// market data first, then the 8 parallel analysis agents, then the
// sequential enrichment steps. Elliott Wave and Wyckoff are marked advisory
// per the spec - they never block a call on their own.
const SECTIONS: { key: keyof MarketContext; title: string; advisory?: boolean }[] = [
  { key: 'market_data', title: 'Market Data' },
  { key: 'technical_analysis', title: 'Technical Analysis' },
  { key: 'price_action', title: 'Price Action' },
  { key: 'candlestick', title: 'Candlestick Patterns' },
  { key: 'support_resistance', title: 'Support & Resistance' },
  { key: 'smc', title: 'Smart Money Concepts (SMC / ICT)' },
  { key: 'elliott_wave', title: 'Elliott Wave', advisory: true },
  { key: 'wyckoff', title: 'Wyckoff', advisory: true },
  { key: 'news', title: 'News & Sentiment' },
  { key: 'historical_similarity', title: 'Historical Similarity' },
  { key: 'risk_analysis', title: 'Risk Analysis' },
  { key: 'learning_metrics', title: 'Learning / Statistics' },
]

// Sized to approximate the real summary card, chart, and a few collapsed
// section panels so nothing jumps once the real detail arrives.
function DetailLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-4 rounded-lg border border-line bg-raised p-5">
        <div className="flex gap-3">
          <Skeleton className="h-6 w-16" />
          <Skeleton className="h-6 w-40" />
        </div>
        <div className="grid grid-cols-2 gap-5">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
        <Skeleton className="h-16 w-full" />
      </div>
      <Skeleton className="h-80 w-full rounded-lg" />
      <div className="flex flex-col gap-2">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-12 w-full rounded-lg" />
        ))}
      </div>
    </div>
  )
}

export function RecommendationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const numericId = Number(id)
  const detail = useRecommendationDetail(numericId)

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Recommendation <span className="font-mono text-ink-soft">#{id}</span>
        </h1>
        <p className="max-w-prose text-ink-soft">
          The full blackboard for this call &mdash; every agent&rsquo;s evidence, not just
          the final verdict.
        </p>
      </div>

      {detail.isLoading && <DetailLoadingSkeleton />}

      {detail.isError && (
        <p className="rounded-md bg-sell-soft px-3 py-2 text-sm text-sell">
          {detail.error instanceof ApiError
            ? detail.error.message
            : 'Could not load this recommendation.'}
        </p>
      )}

      {detail.isSuccess && (
        <>
          {detail.data.market_context.reasoning_output ? (
            <RecommendationResult
              result={{
                as_of: detail.data.created_at,
                recommendation: detail.data.market_context.reasoning_output,
                conflicts: detail.data.market_context.conflicts ?? [],
              }}
              extra={<OutcomeChip value={detail.data.status} />}
            />
          ) : (
            <p className="text-sm text-ink-soft">
              No final verdict was recorded for this call.
            </p>
          )}

          <RecommendationChart
            createdAt={detail.data.created_at}
            marketContext={detail.data.market_context}
            reasoning={detail.data.market_context.reasoning_output}
          />

          <div className="flex flex-col gap-2">
            {SECTIONS.map(({ key, title, advisory }) => {
              const data = detail.data.market_context[key] as
                MarketContextSection | null | undefined
              if (!data || Object.keys(data).length === 0) return null
              return (
                <AgentSectionPanel
                  key={key}
                  title={title}
                  advisory={advisory}
                  data={data}
                />
              )
            })}
          </div>

          <ChatPanel recommendationId={detail.data.id} />
        </>
      )}
    </div>
  )
}
