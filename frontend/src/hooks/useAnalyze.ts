import { useMutation } from '@tanstack/react-query'
import { postAnalyze } from '../api/endpoints'

/** POST /api/analyze - a mutation, not a query: each call is a fresh, non-idempotent
 * 15-30s pipeline run, never something to cache or refetch silently in the background. */
export function useAnalyze() {
  return useMutation({
    mutationFn: (symbol: string) => postAnalyze(symbol),
  })
}
