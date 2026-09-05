export type RecommendationStatus = 'BUY' | 'SELL' | 'WAIT'
export type OutcomeStatus = 'WIN' | 'LOSS' | 'PENDING' | 'EXPIRED'

const recommendationClasses: Record<RecommendationStatus, string> = {
  BUY: 'bg-buy-soft text-buy',
  SELL: 'bg-sell-soft text-sell',
  WAIT: 'bg-wait-soft text-wait',
}

const outcomeClasses: Record<OutcomeStatus, string> = {
  WIN: 'bg-win-soft text-win',
  LOSS: 'bg-loss-soft text-loss',
  PENDING: 'bg-pending-soft text-pending',
  EXPIRED: 'bg-expired-soft text-expired',
}

const chipBase =
  'inline-flex items-center rounded-md px-2.5 py-1 font-mono text-xs font-semibold tracking-wide uppercase'

export function RecommendationChip({ value }: { value: RecommendationStatus }) {
  return <span className={`${chipBase} ${recommendationClasses[value]}`}>{value}</span>
}

export function OutcomeChip({ value }: { value: OutcomeStatus }) {
  return <span className={`${chipBase} ${outcomeClasses[value]}`}>{value}</span>
}
