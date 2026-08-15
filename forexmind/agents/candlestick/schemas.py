"""Structured output shape for the Candlestick Agent — what gets written onto
the ``candlestick`` section of the blackboard
(see orchestration/market_context.py).

Each detected pattern is a ``CandlestickPattern``; the top-level
``CandlestickSnapshot`` groups them by timeframe.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CandlestickPattern(BaseModel):
    """A single detected candlestick pattern."""

    name: str
    """Human-readable pattern name, e.g. ``"hammer"``, ``"bullish_engulfing"``."""

    type: str
    """``"single"`` or ``"multi"``."""

    direction: str
    """``"bullish"``, ``"bearish"``, or ``"neutral"``."""

    candle_index: int
    """0-based index in the OHLC DataFrame where the pattern completed
    (i.e. the last candle of the pattern)."""

    timestamp: str
    """Timestamp string of the triggering candle."""


class CandlestickSnapshot(BaseModel):
    """Top-level output of the Candlestick Agent.

    ``timeframes`` maps interval strings (e.g. ``"1day"``, ``"4h"``) to the
    list of patterns detected on that timeframe's candle data.
    """

    as_of: str
    timeframes: dict[str, list[CandlestickPattern]] = Field(default_factory=dict)
