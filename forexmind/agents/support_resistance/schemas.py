from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


LevelType = Literal["horizontal", "psychological", "dynamic"]


class PriceLevel(BaseModel):
    """Represents a support or resistance price level or narrow zone."""

    price: float
    type: LevelType
    strength: Literal["strong", "moderate", "weak"]
    touch_count: int = 1
    # For horizontal levels, the range of prices that make up the zone
    zone_high: float | None = None
    zone_low: float | None = None
    # For dynamic levels, the indicator used (e.g. "EMA_50")
    source: str | None = None


class SupportResistanceResult(BaseModel):
    """The identified support and resistance levels for a single timeframe."""

    # Ranked lists of levels, closest to current price first, or strongest first
    support_levels: list[PriceLevel] = Field(default_factory=list)
    resistance_levels: list[PriceLevel] = Field(default_factory=list)


class SupportResistanceSnapshot(BaseModel):
    """A multi-timeframe snapshot of support and resistance levels."""

    as_of: str | None = None
    timeframes: dict[str, SupportResistanceResult] = Field(default_factory=dict)
