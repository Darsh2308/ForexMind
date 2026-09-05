import type { ReactNode } from 'react'
import type { ReasoningSnapshot } from '../types/api'
import { ConfidenceMeter } from './ConfidenceMeter'
import { EvidenceList } from './EvidenceList'
import { LlmProviderBadge } from './LlmProviderBadge'
import { PriceLevels } from './PriceLevels'
import { QualityScore } from './QualityScore'
import { RecommendationChip } from './StatusChip'

export interface RecommendationResultData {
  as_of: string
  recommendation: ReasoningSnapshot
  conflicts: string[]
}

export function RecommendationResult({
  result,
  extra,
}: {
  result: RecommendationResultData
  /** Slot for context this component doesn't own - e.g. the resolved WIN/LOSS
   * outcome badge on the Phase 4 detail page, absent on a fresh Phase 2 call. */
  extra?: ReactNode
}) {
  const rec = result.recommendation

  return (
    <section className="flex flex-col gap-5 rounded-lg border border-line bg-raised p-5">
      <header className="flex flex-wrap items-center gap-3">
        <RecommendationChip value={rec.recommendation} />
        <span className="font-mono text-xs text-ink-faint">{result.as_of}</span>
        {extra}
        <div className="ml-auto">
          <LlmProviderBadge provider={rec.llm_provider} />
        </div>
      </header>

      {/* Contradictions must stay visible, not get silently dropped (spec §8) -
          rendered first, prominent, never collapsed. */}
      {result.conflicts.length > 0 && (
        <div className="rounded-md bg-wait-soft px-3 py-2.5 text-sm text-wait">
          <b className="font-mono text-xs tracking-wide uppercase">
            Conflicting signals across agents
          </b>
          <ul className="mt-1.5 flex flex-col gap-1">
            {result.conflicts.map((conflict) => (
              <li key={conflict}>{conflict}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <ConfidenceMeter
          confidence={rec.confidence}
          recommendation={rec.recommendation}
        />
        <QualityScore score={rec.trade_quality_score} />
      </div>

      <PriceLevels
        entry={rec.entry}
        stopLoss={rec.stop_loss}
        takeProfit={rec.take_profit}
        rewardToRisk={rec.reward_to_risk}
      />

      <div>
        <h2 className="font-mono text-xs font-medium tracking-wide text-ink-faint uppercase">
          Reasoning
        </h2>
        <p className="mt-1.5 text-sm text-ink">{rec.reasoning}</p>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <EvidenceList
          title="Supporting evidence"
          items={rec.supporting_evidence}
          tone="supporting"
        />
        <EvidenceList
          title="Conflicting evidence"
          items={rec.conflicting_evidence}
          tone="conflicting"
        />
      </div>

      <EvidenceList title="Important news" items={rec.important_news} tone="neutral" />

      {rec.historical_similarity != null && (
        <p className="font-mono text-xs text-ink-faint">
          {Math.round(rec.historical_similarity * 100)}% similar to past setups on record.
        </p>
      )}
    </section>
  )
}
