"""Structured output shape for the Elliott Wave Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Wave(BaseModel):
    """Represents a single detected wave (1, 2, 3, 4, 5, A, B, C)."""

    label: str
    """E.g., '1', '2', '3', '4', '5', 'A', 'B', 'C'"""
    
    start_index: int
    end_index: int
    start_price: float
    end_price: float


class WaveCount(BaseModel):
    """A collection of waves forming a pattern."""

    pattern_type: str = "none"
    """'motive' (1-2-3-4-5) or 'corrective' (A-B-C) or 'none'"""
    
    degree: str = "minor"
    """The timescale degree (e.g., 'minor', 'intermediate')"""
    
    waves: list[Wave] = Field(default_factory=list)
    
    confidence: float = 0.0
    """Advisory confidence score (0.0 to 1.0) for this count"""
    
    is_valid: bool = False
    """Whether the count passed all classical validation rules (e.g., Wave 3 not shortest)"""


class ElliottWaveResult(BaseModel):
    """Elliott Wave analysis for a single timeframe."""
    
    current_count: WaveCount = Field(default_factory=WaveCount)


class ElliottWaveSnapshot(BaseModel):
    """Top-level output of the Elliott Wave Agent."""
    
    as_of: str
    timeframes: dict[str, ElliottWaveResult] = Field(default_factory=dict)
