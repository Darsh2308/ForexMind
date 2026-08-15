"""Structured output shape for the News Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    """Represents a single parsed news article."""

    headline: str
    summary: str = ""
    timestamp: str
    
    sentiment_score: float = 0.0
    """Compound sentiment score (-1.0 to 1.0)"""
    
    sentiment_label: str = "neutral"
    """'bullish', 'bearish', or 'neutral'"""
    
    time_decay_weight: float = 1.0
    """Relevance weight based on how old the article is (0.0 to 1.0)"""


class EconomicEvent(BaseModel):
    """Represents an economic calendar event."""

    event_name: str
    impact: str
    """'high', 'medium', 'low'"""
    
    expected: str | None = None
    actual: str | None = None
    
    timestamp: str
    
    sentiment_label: str = "neutral"
    """Inferred sentiment based on actual vs expected if available"""
    
    time_decay_weight: float = 1.0
    """Relevance weight based on how old the event is (0.0 to 1.0)"""


class NewsSnapshot(BaseModel):
    """Top-level output of the News Agent."""

    as_of: str
    
    overall_sentiment: str = "neutral"
    """Aggregated sentiment across all recent weighted articles and events"""
    
    articles: list[NewsArticle] = Field(default_factory=list)
    events: list[EconomicEvent] = Field(default_factory=list)
