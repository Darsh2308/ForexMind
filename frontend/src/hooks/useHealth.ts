import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../api/endpoints'

/** GET /health, polled - backs the Phase 6 status widget and the small
 * footer indicator wired up in Phase 0/1. */
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => getHealth(signal),
    refetchInterval: 60_000,
    retry: 1,
  })
}
