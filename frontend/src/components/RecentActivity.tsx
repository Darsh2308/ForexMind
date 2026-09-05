import { Link } from 'react-router-dom'
import type { RecommendationHistoryItem } from '../types/api'
import { OutcomeChip, RecommendationChip } from './StatusChip'

export function RecentActivity({ items }: { items: RecommendationHistoryItem[] }) {
  const recent = items.slice(0, 5)

  return (
    <section className="flex flex-col gap-2 rounded-lg border border-line bg-raised p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-mono text-xs font-medium tracking-wide text-ink-faint uppercase">
          Recent activity
        </h2>
        <Link to="/history" className="font-mono text-xs text-accent hover:underline">
          View all &rarr;
        </Link>
      </div>

      {recent.length === 0 ? (
        <p className="text-sm text-ink-faint">No recommendations yet.</p>
      ) : (
        <ul className="flex flex-col divide-y divide-line">
          {recent.map((item) => (
            <li key={item.id}>
              <Link
                to={`/history/${item.id}`}
                className="flex flex-col gap-1.5 py-2.5 hover:bg-accent-soft sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="font-mono text-xs text-ink-faint">
                  {item.created_at}
                </span>
                <div className="flex items-center gap-3 sm:contents">
                  <RecommendationChip value={item.recommendation} />
                  <OutcomeChip value={item.status} />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
