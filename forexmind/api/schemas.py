from pydantic import BaseModel, Field
from typing import Any, Literal
from forexmind.agents.reasoning.schemas import ReasoningSnapshot

class AnalyzeRequest(BaseModel):
    symbol: str

class AnalyzeResponse(BaseModel):
    symbol: str
    as_of: str
    recommendation: ReasoningSnapshot
    conflicts: list[str]

class RecommendationHistoryItem(BaseModel):
    id: int
    created_at: str
    recommendation: str
    entry: float | None
    stop_loss: float | None
    take_profit: float | None
    status: str

class HistoryResponse(BaseModel):
    recommendations: list[RecommendationHistoryItem]

class CandleItem(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None

class CandlesResponse(BaseModel):
    interval: str
    candles: list[CandleItem]

class RecommendationDetailResponse(BaseModel):
    """The full blackboard (MarketContext) for one past recommendation -
    Phase 4 of frontend/Development.md's evidence drill-down. `market_context`
    is returned as a raw dict rather than re-declared field-by-field here:
    its true shape is `MarketContext.model_dump_json()` from
    orchestration/market_context.py, which already owns that schema."""
    id: int
    created_at: str
    status: str
    market_context: dict[str, Any]

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    # Omit to chat "cold" - the endpoint grounds itself in the latest
    # recommendation, running a fresh analysis first if none exists yet or
    # the latest one is stale.
    recommendation_id: int | None = None
    message: str
    # Last few turns, sent by the client each call - no server-side chat
    # history table exists yet, matching this feature's intentionally small
    # first-cut scope (see frontend/Development.md's dashboard redesign note).
    history: list[ChatMessage] = Field(default_factory=list)

class ChatResponse(BaseModel):
    reply: str
    llm_provider: Literal["groq", "ollama", "fallback"]
    # The recommendation this reply is grounded in. None only if a fresh
    # analysis was triggered and it came back WAIT (never persisted).
    recommendation_id: int | None = None
    triggered_new_analysis: bool = False
