"""Structured output shape for the Price Action Agent — what gets written onto
the ``price_action`` section of the blackboard
(see orchestration/market_context.py).

The agent classifies trend, detects breakouts/pullbacks/rejections, and
identifies range-bound conditions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TrendState(BaseModel):
    """Current trend classification based on swing-point structure."""

    direction: str = "ranging"
    """``"bullish"``, ``"bearish"``, or ``"ranging"``."""

    strength: str = "weak"
    """``"strong"``, ``"moderate"``, or ``"weak"``."""

    higher_highs: bool = False
    higher_lows: bool = False
    lower_highs: bool = False
    lower_lows: bool = False


class BreakoutSignal(BaseModel):
    """A detected breakout event."""

    detected: bool = False
    direction: str = "neutral"
    """``"bullish"`` or ``"bearish"``."""

    breakout_level: float | None = None
    candle_index: int | None = None
    timestamp: str | None = None


class PullbackSignal(BaseModel):
    """A detected pullback (retracement against the prevailing trend)."""

    detected: bool = False
    direction: str = "neutral"
    """Direction of the *resumed trend*, not the pullback itself.
    ``"bullish"`` means price pulled back down then resumed up."""

    depth_pct: float | None = None
    """How deep the pullback went as a percentage of the prior move."""

    candle_index: int | None = None
    timestamp: str | None = None


class RangeState(BaseModel):
    """Range/consolidation detection."""

    detected: bool = False
    range_high: float | None = None
    range_low: float | None = None
    duration_bars: int | None = None


class RejectionSignal(BaseModel):
    """A wick-rejection of a price level."""

    detected: bool = False
    level: float | None = None
    direction: str = "neutral"
    """``"bullish"`` (rejected from below, bounced up) or ``"bearish"``
    (rejected from above, pushed down)."""

    candle_index: int | None = None
    timestamp: str | None = None


class PriceActionResult(BaseModel):
    """Aggregated price-action analysis for a single timeframe."""

    trend: TrendState = Field(default_factory=TrendState)
    breakouts: list[BreakoutSignal] = Field(default_factory=list)
    pullbacks: list[PullbackSignal] = Field(default_factory=list)
    range_state: RangeState = Field(default_factory=RangeState)
    rejections: list[RejectionSignal] = Field(default_factory=list)


class PriceActionSnapshot(BaseModel):
    """Top-level output of the Price Action Agent.

    ``timeframes`` maps interval strings (e.g. ``"1day"``, ``"4h"``) to
    their ``PriceActionResult``.
    """

    as_of: str
    timeframes: dict[str, PriceActionResult] = Field(default_factory=dict)
