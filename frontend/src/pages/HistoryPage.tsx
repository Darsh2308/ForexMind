import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  HistoryFilters,
  type RecommendationFilter,
  type SortOrder,
  type StatusFilter,
} from '../components/HistoryFilters'
import { Skeleton } from '../components/Skeleton'
import { OutcomeChip, RecommendationChip } from '../components/StatusChip'
import { useHistory } from '../hooks/useHistory'

// Sized to approximate a real row (HistoryFilters + 5 rows) so nothing jumps
// once the real list arrives.
function HistoryLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-8 w-36" />
        <Skeleton className="h-8 w-28" />
      </div>
      <div className="flex flex-col divide-y divide-line rounded-lg border border-line bg-raised">
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="flex items-center justify-between gap-3 px-4 py-3">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-5 w-14" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-5 w-16" />
          </div>
        ))}
      </div>
    </div>
  )
}

export function HistoryPage() {
  const history = useHistory()

  const [sortOrder, setSortOrder] = useState<SortOrder>('newest')
  const [recommendationFilter, setRecommendationFilter] =
    useState<RecommendationFilter>('ALL')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')

  const rows = useMemo(() => {
    const all = history.data?.recommendations ?? []
    const filtered = all.filter(
      (item) =>
        (recommendationFilter === 'ALL' ||
          item.recommendation === recommendationFilter) &&
        (statusFilter === 'ALL' || item.status === statusFilter),
    )
    // The API already returns newest-first; only re-sort when the user asks
    // for the opposite order, rather than re-sorting on every render.
    return sortOrder === 'newest' ? filtered : [...filtered].reverse()
  }, [history.data, sortOrder, recommendationFilter, statusFilter])

  const hasAnyRecommendations = (history.data?.recommendations.length ?? 0) > 0

  return (
    <div className="flex flex-col gap-3">
      <h1 className="text-2xl font-semibold tracking-tight">Recommendation history</h1>
      <p className="max-w-prose text-ink-soft">
        Every past call, its status, and how it resolved.
      </p>

      {history.isLoading && <HistoryLoadingSkeleton />}

      {history.isError && (
        <p className="rounded-md bg-sell-soft px-3 py-2 text-sm text-sell">
          {history.error instanceof ApiError
            ? history.error.message
            : 'Could not load history.'}
        </p>
      )}

      {history.isSuccess && !hasAnyRecommendations && (
        <div className="mt-2 rounded-lg border border-dashed border-line p-8 text-center text-sm text-ink-faint">
          No recommendations yet &mdash; run an analysis first.
        </div>
      )}

      {history.isSuccess && hasAnyRecommendations && (
        <>
          <HistoryFilters
            sortOrder={sortOrder}
            onSortOrderChange={setSortOrder}
            recommendationFilter={recommendationFilter}
            onRecommendationFilterChange={setRecommendationFilter}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
          />

          {rows.length === 0 ? (
            <div className="mt-2 rounded-lg border border-dashed border-line p-8 text-center text-sm text-ink-faint">
              No recommendations match these filters.
            </div>
          ) : (
            <ul className="mt-2 flex flex-col divide-y divide-line rounded-lg border border-line bg-raised">
              {rows.map((item) => (
                <li key={item.id}>
                  {/* Two lines on mobile (timestamp, then the fixed-width
                      badges/price on their own row so their spacing stays
                      consistent) collapse into `sm:contents` on wider
                      screens, becoming one flex row via the parent Link. */}
                  <Link
                    to={`/history/${item.id}`}
                    className="flex flex-col gap-1.5 px-4 py-3 hover:bg-accent-soft sm:flex-row sm:items-center sm:justify-between"
                  >
                    <span className="font-mono text-xs text-ink-faint">
                      {item.created_at}
                    </span>
                    <div className="flex items-center justify-between gap-3 sm:contents">
                      <RecommendationChip value={item.recommendation} />
                      <span className="font-mono text-xs text-ink-soft tabular-nums">
                        {item.entry === null ? '—' : item.entry.toFixed(5)}
                      </span>
                      <OutcomeChip value={item.status} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}
