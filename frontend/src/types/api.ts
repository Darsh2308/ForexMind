/**
 * Hand-written mirrors of the backend's Pydantic schemas
 * (forexmind/api/schemas.py, forexmind/agents/reasoning/schemas.py).
 * Keep these in sync by hand - see Development.md §0 for why there's no
 * OpenAPI codegen step yet.
 */

export type Recommendation = 'BUY' | 'SELL' | 'WAIT'
export type RecommendationStatus = 'PENDING' | 'WIN' | 'LOSS' | 'EXPIRED'
export type LlmProvider = 'groq' | 'ollama' | 'fallback'

/**
 * Mirrors forexmind/agents/reasoning/schemas.py::ReasoningSnapshot.
 *
 * The optional fields below are `| undefined` as well as `| null`: a live
 * POST /api/analyze response includes them as explicit JSON `null`, but a
 * GET /api/recommendation/{id} response reads back a MarketContext that was
 * persisted with Pydantic's `exclude_none=True` - those keys are simply
 * absent from that stored JSON, i.e. `undefined` once parsed. Always check
 * with `== null`, not `=== null`, so both sources are handled the same way.
 */
export interface ReasoningSnapshot {
  recommendation: Recommendation
  confidence: number

  entry: number | null | undefined
  stop_loss: number | null | undefined
  take_profit: number | null | undefined

  reasoning: string
  supporting_evidence: string[]
  conflicting_evidence: string[]

  historical_similarity: number | null | undefined
  reward_to_risk: number | null | undefined

  important_news: string[]
  trade_quality_score: number

  llm_provider: LlmProvider | null | undefined
}

/** Mirrors forexmind/api/schemas.py::AnalyzeRequest */
export interface AnalyzeRequest {
  symbol: string
}

/** Mirrors forexmind/api/schemas.py::AnalyzeResponse */
export interface AnalyzeResponse {
  symbol: string
  as_of: string
  recommendation: ReasoningSnapshot
  conflicts: string[]
}

/** Mirrors forexmind/api/schemas.py::RecommendationHistoryItem */
export interface RecommendationHistoryItem {
  id: number
  created_at: string
  recommendation: Recommendation
  entry: number | null
  stop_loss: number | null
  take_profit: number | null
  status: RecommendationStatus
}

/** Mirrors forexmind/api/schemas.py::HistoryResponse */
export interface HistoryResponse {
  recommendations: RecommendationHistoryItem[]
}

/** Mirrors the two possible shapes forexmind/api/app.py::health() returns. */
export type HealthResponse =
  { status: 'ok'; alerts_last_24h: number } | { status: 'degraded'; detail: string }

/**
 * One agent's section of the blackboard - shape varies per agent (see
 * orchestration/market_context.py) and is rendered generically by
 * StructuredValue rather than mirrored field-by-field: hand-typing all 11
 * analysis agents' schemas (each with its own multi-timeframe nested
 * indicators/patterns/zones) is out of proportion to what Phase 4 needs.
 */
export type MarketContextSection = Record<string, unknown>

/** Mirrors orchestration/market_context.py::MarketContext. Sections are
 * omitted by the backend's `exclude_none=True, exclude_defaults=True` dump
 * when null/empty, hence the optional markers throughout. */
export interface MarketContext {
  generated_at: string
  symbol: string
  timeframes?: string[]
  conflicts?: string[]
  reasoning_output?: ReasoningSnapshot | null

  market_data?: MarketContextSection | null
  technical_analysis?: MarketContextSection | null
  price_action?: MarketContextSection | null
  candlestick?: MarketContextSection | null
  support_resistance?: MarketContextSection | null
  smc?: MarketContextSection | null
  elliott_wave?: MarketContextSection | null
  wyckoff?: MarketContextSection | null
  news?: MarketContextSection | null
  historical_similarity?: MarketContextSection | null
  risk_analysis?: MarketContextSection | null
  learning_metrics?: MarketContextSection | null
}

/** Mirrors forexmind/api/schemas.py::CandleItem */
export interface Candle {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number | null
}

/** Mirrors forexmind/api/schemas.py::CandlesResponse */
export interface CandlesResponse {
  interval: string
  candles: Candle[]
}

/** Mirrors forexmind/api/schemas.py::RecommendationDetailResponse */
export interface RecommendationDetail {
  id: number
  created_at: string
  status: RecommendationStatus
  market_context: MarketContext
}

/** Mirrors forexmind/api/schemas.py::ChatMessage */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/** Mirrors forexmind/api/schemas.py::ChatRequest. `recommendation_id` is
 * null for "cold" chat - the backend grounds on the latest recommendation,
 * running a fresh analysis first if none exists yet or it's stale. */
export interface ChatRequest {
  recommendation_id: number | null
  message: string
  history: ChatMessage[]
}

/** Mirrors forexmind/api/schemas.py::ChatResponse */
export interface ChatResponse {
  reply: string
  llm_provider: LlmProvider
  /** The recommendation this reply is grounded in. Null only if a fresh
   * "cold" analysis was triggered and it came back WAIT (never persisted). */
  recommendation_id: number | null
  /** True if answering this message required running a fresh analysis
   * (no recent recommendation existed to ground on). */
  triggered_new_analysis: boolean
}
