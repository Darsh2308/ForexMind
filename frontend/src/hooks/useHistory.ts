import { useQuery } from '@tanstack/react-query'
import { getHistory } from '../api/endpoints'

/** GET /api/history */
export function useHistory(limit = 50) {
  return useQuery({
    queryKey: ['history', limit],
    queryFn: ({ signal }) => getHistory(limit, signal),
  })
}
