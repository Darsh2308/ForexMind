"""Structured output shape for the Technical Analysis Agent — what gets written
onto the `technical_analysis` section of the blackboard
(see orchestration/market_context.py).

Each timeframe analysed gets its own `IndicatorSet`; the top-level
`TechnicalAnalysisSnapshot` wraps them all.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class IndicatorSet(BaseModel):
    """All indicator values for a single timeframe.

    Every numeric field is Optional — if there aren't enough candles for a
    given indicator (e.g. EMA-200 needs 200+ bars), the field stays None
    rather than raising or fabricating a value.
    """

    # ── Trend ──────────────────────────────────────────────────────────
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None

    ema_20_above_ema_50: bool | None = None
    ema_50_above_ema_200: bool | None = None

    # "bullish" | "bearish" | "neutral"
    trend: str = "neutral"

    # ── Momentum ───────────────────────────────────────────────────────
    rsi_14: float | None = None
    # "overbought" | "oversold" | "neutral"
    rsi_zone: str = "neutral"

    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    # "bullish" | "bearish" | "none"
    macd_cross: str = "none"

    stoch_k: float | None = None
    stoch_d: float | None = None
    # "overbought" | "oversold" | "neutral"
    stoch_zone: str = "neutral"

    # ── Volatility ─────────────────────────────────────────────────────
    atr_14: float | None = None

    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    bb_bandwidth: float | None = None
    # (close - lower) / (upper - lower) — position within the bands
    bb_percent_b: float | None = None


class TechnicalAnalysisSnapshot(BaseModel):
    """Top-level output of the Technical Analysis Agent.

    `timeframes` maps interval strings (e.g. "1day", "4h") to their
    computed indicator sets.
    """

    as_of: str
    timeframes: dict[str, IndicatorSet] = Field(default_factory=dict)
