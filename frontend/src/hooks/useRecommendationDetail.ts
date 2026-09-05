import { useQuery } from '@tanstack/react-query'
import { getRecommendationDetail } from '../api/endpoints'

/** GET /api/recommendation/{id} */
export function useRecommendationDetail(id: number) {
  return useQuery({
    queryKey: ['recommendation', id],
    queryFn: ({ signal }) => getRecommendationDetail(id, signal),
    enabled: Number.isFinite(id),
  })
}
