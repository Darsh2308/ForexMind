import { useQuery } from '@tanstack/react-query'
import { getCandles } from '../api/endpoints'

const POLL_INTERVAL_MS = 60_000

/**
 * Polls GET /api/candles for "as of right now," re-reading the local
 * SQLite-backed endpoint every 60s - no Twelve Data calls, so no rate-limit
 * risk. `asOf` is deliberately NOT part of the query key: a fixed key lets
 * TanStack Query treat this as one ongoing poll rather than growing a new
 * cache entry every tick, while the queryFn itself recomputes "now" on each
 * call so a genuinely new candle (from a live analyze run elsewhere) would
 * actually show up.
 *
 * Honest limitation: nothing in this app inserts fresh live candles into
 * SQLite on a timer (that's the deferred APScheduler gap from the backend's
 * own Development.md) - so this shows the most recent data actually stored,
 * not a continuously-ticking feed. See frontend/Development.md's dashboard
 * redesign note.
 */
// Matches the backend's own `datetime.strftime("%Y-%m-%dT%H:%M:%SZ")` format
// exactly (no milliseconds) - candles/db.py's lookahead-safe comparison is a
// plain string compare, so staying byte-for-byte consistent with what the
// backend itself produces avoids relying on incidental ASCII-ordering luck.
function nowAsBackendTimestamp(): string {
  return `${new Date().toISOString().slice(0, 19)}Z`
}

export function useLiveCandles(interval: string, limit = 100) {
  return useQuery({
    queryKey: ['live-candles', interval, limit],
    queryFn: ({ signal }) => getCandles(interval, nowAsBackendTimestamp(), limit, signal),
    refetchInterval: POLL_INTERVAL_MS,
  })
}
