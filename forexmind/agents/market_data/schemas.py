"""Structured output shape for the Market Data Agent - what gets written onto
the `market_data` section of the blackboard (see orchestration/market_context.py)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Candle(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class SessionState(BaseModel):
    active_sessions: list[str] = Field(default_factory=list)
    overlaps: list[str] = Field(default_factory=list)


class MarketDataSnapshot(BaseModel):
    as_of: str
    symbol: str = "EUR/USD"
    is_live: bool

    # Live-only fields. Twelve Data's free-tier /quote has no bid/ask, so
    # spread is always None for now - not a bug, see TwelveDataClient.get_quote.
    latest_price: float | None = None
    spread: float | None = None
    is_market_open: bool | None = None

    sessions: SessionState
    # interval (e.g. "15min", "1day") -> most recent candle at/before as_of.
    # Missing key means no stored candle exists at/before as_of for that
    # interval (not yet backfilled, or as_of predates available history).
    timeframes: dict[str, Candle] = Field(default_factory=dict)
