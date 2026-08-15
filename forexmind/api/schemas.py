from pydantic import BaseModel
from typing import Any
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
