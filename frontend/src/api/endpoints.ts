import { apiFetch } from './client'
import type {
  AnalyzeResponse,
  CandlesResponse,
  ChatMessage,
  ChatResponse,
  HealthResponse,
  HistoryResponse,
  RecommendationDetail,
} from '../types/api'

export function postAnalyze(
  symbol: string,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  return apiFetch<AnalyzeResponse>('/api/analyze', {
    method: 'POST',
    body: { symbol },
    signal,
  })
}

export function getHistory(limit = 50, signal?: AbortSignal): Promise<HistoryResponse> {
  return apiFetch<HistoryResponse>(`/api/history?limit=${limit}`, { signal })
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health', { signal })
}

export function getCandles(
  interval: string,
  asOf: string,
  limit = 200,
  signal?: AbortSignal,
): Promise<CandlesResponse> {
  const params = new URLSearchParams({ interval, as_of: asOf, limit: String(limit) })
  return apiFetch<CandlesResponse>(`/api/candles?${params}`, { signal })
}

export function getRecommendationDetail(
  id: number,
  signal?: AbortSignal,
): Promise<RecommendationDetail> {
  return apiFetch<RecommendationDetail>(`/api/recommendation/${id}`, { signal })
}

export function postChat(
  recommendationId: number | null,
  message: string,
  history: ChatMessage[],
  signal?: AbortSignal,
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/api/chat', {
    method: 'POST',
    body: { recommendation_id: recommendationId, message, history },
    signal,
  })
}
