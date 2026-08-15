from typing import Literal
from pydantic import BaseModel, Field

class ReasoningSnapshot(BaseModel):
    """The final structured recommendation provided by the LLM Reasoning Agent."""
    
    recommendation: Literal["BUY", "SELL", "WAIT"]
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    
    reasoning: str = Field(..., description="Detailed explanation of why this recommendation was made.")
    supporting_evidence: list[str] = Field(..., description="List of bullish/bearish signals supporting the trade.")
    conflicting_evidence: list[str] = Field(..., description="List of signals that conflict with the trade.")
    
    historical_similarity: float | None = None
    reward_to_risk: float | None = None
    
    important_news: list[str] = Field(..., description="Any highly relevant news affecting this instrument.")
    trade_quality_score: int = Field(..., ge=1, le=10, description="Overall quality score from 1 to 10.")
