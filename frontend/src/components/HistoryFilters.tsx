import type { Recommendation, RecommendationStatus } from '../types/api'

export type SortOrder = 'newest' | 'oldest'
export type RecommendationFilter = 'ALL' | Recommendation
export type StatusFilter = 'ALL' | RecommendationStatus

const selectClass =
  'rounded-md border border-line bg-raised px-2.5 py-1.5 font-mono text-xs text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent'

export function HistoryFilters({
  sortOrder,
  onSortOrderChange,
  recommendationFilter,
  onRecommendationFilterChange,
  statusFilter,
  onStatusFilterChange,
}: {
  sortOrder: SortOrder
  onSortOrderChange: (value: SortOrder) => void
  recommendationFilter: RecommendationFilter
  onRecommendationFilterChange: (value: RecommendationFilter) => void
  statusFilter: StatusFilter
  onStatusFilterChange: (value: StatusFilter) => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        aria-label="Sort by date"
        className={selectClass}
        value={sortOrder}
        onChange={(e) => onSortOrderChange(e.target.value as SortOrder)}
      >
        <option value="newest">Newest first</option>
        <option value="oldest">Oldest first</option>
      </select>

      <select
        aria-label="Filter by recommendation"
        className={selectClass}
        value={recommendationFilter}
        onChange={(e) =>
          onRecommendationFilterChange(e.target.value as RecommendationFilter)
        }
      >
        <option value="ALL">All recommendations</option>
        <option value="BUY">BUY</option>
        <option value="SELL">SELL</option>
        <option value="WAIT">WAIT</option>
      </select>

      <select
        aria-label="Filter by status"
        className={selectClass}
        value={statusFilter}
        onChange={(e) => onStatusFilterChange(e.target.value as StatusFilter)}
      >
        <option value="ALL">All statuses</option>
        <option value="PENDING">PENDING</option>
        <option value="WIN">WIN</option>
        <option value="LOSS">LOSS</option>
        <option value="EXPIRED">EXPIRED</option>
      </select>
    </div>
  )
}
