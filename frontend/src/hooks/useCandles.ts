import { useQuery } from '@tanstack/react-query'
import { getCandles } from '../api/endpoints'

/** GET /api/candles - `enabled` so callers can wait until they know which
 * interval/as_of to ask for (e.g. a recommendation's own timeframe). */
export function useCandles(interval: string, asOf: string, limit = 200) {
  return useQuery({
    queryKey: ['candles', interval, asOf, limit],
    queryFn: ({ signal }) => getCandles(interval, asOf, limit, signal),
    enabled: Boolean(interval && asOf),
  })
}
