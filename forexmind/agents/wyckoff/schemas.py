"""Structured output shape for the Wyckoff Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WyckoffPhase(BaseModel):
    """Represents a detected Wyckoff phase."""
    
    phase: str = "unknown"
    """'accumulation', 'markup', 'distribution', 'markdown', or 'unknown'"""
    
    confidence: float = 0.0
    """Advisory confidence score (0.0 to 1.0)"""
    
    support_level: float | None = None
    resistance_level: float | None = None


class SpringUpthrustEvent(BaseModel):
    """A specific event typical of accumulation/distribution phases."""
    
    event_type: str = "none"
    """'spring', 'upthrust', or 'none'"""
    
    price_level: float | None = None
    candle_index: int | None = None


class WyckoffResult(BaseModel):
    """Wyckoff analysis for a single timeframe."""
    
    current_phase: WyckoffPhase = Field(default_factory=WyckoffPhase)
    events: list[SpringUpthrustEvent] = Field(default_factory=list)


class WyckoffSnapshot(BaseModel):
    """Top-level output of the Wyckoff Agent."""
    
    as_of: str
    timeframes: dict[str, WyckoffResult] = Field(default_factory=dict)
