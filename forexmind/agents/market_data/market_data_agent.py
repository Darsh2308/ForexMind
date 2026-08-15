"""Agent 1: Market Data Agent.

Owns everything IO-related for market data - live price, historical backfill,
and reconstructing the multi-timeframe OHLC state as of any timestamp (live
or historical, so the exact same code path serves both the live pipeline and
future backtesting in Phase 16).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone

from forexmind.agents.market_data.schemas import Candle, MarketDataSnapshot, SessionState
from forexmind.agents.market_data.sessions import active_sessions, session_overlaps
from forexmind.agents.market_data.twelve_data_client import TwelveDataClient, TwelveDataError
from forexmind.storage.db import fetch_latest_candle_at_or_before, insert_candle

logger = logging.getLogger(__name__)

# Per §6 of the spec: scalp/intraday/swing/long-term-context timeframes.
TIMEFRAMES: list[str] = ["1min", "5min", "15min", "30min", "1h", "4h", "1day", "1week"]

# A snapshot is treated as "live" (and thus eligible for a real quote() call)
# only when as_of is within this window of wall-clock now - anything older is
# an explicitly historical/backtest request and must rely solely on stored
# candles, never on a live API call.
_LIVE_WINDOW = timedelta(minutes=1)


class MarketDataAgent:
    def __init__(self, client: TwelveDataClient, conn: sqlite3.Connection):
        self._client = client
        self._conn = conn

    def backfill_timeframe(self, interval: str, outputsize: int = 500) -> int:
        candles = self._client.get_time_series(interval=interval, outputsize=outputsize)
        for candle in candles:
            insert_candle(
                self._conn,
                interval,
                candle["timestamp"],
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
                candle["volume"],
            )
        logger.info("Backfilled %d candles for interval=%s", len(candles), interval)
        return len(candles)

    def backfill_all_timeframes(self, outputsize: int = 500) -> dict[str, int]:
        results: dict[str, int] = {}
        for interval in TIMEFRAMES:
            try:
                results[interval] = self.backfill_timeframe(interval, outputsize)
            except TwelveDataError as exc:
                logger.error("Backfill failed for interval=%s: %s", interval, exc)
                results[interval] = 0
        return results

    def _as_of_string(self, as_of: datetime) -> str:
        """Matches Twelve Data's UTC timestamp format so string comparison
        against stored rows is chronologically correct (see db.fetch_latest_candle_at_or_before)."""
        return as_of.strftime("%Y-%m-%d %H:%M:%S")

    def get_snapshot(self, as_of: datetime | None = None) -> MarketDataSnapshot:
        now = datetime.now(timezone.utc)
        as_of = as_of or now
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)
        is_live = (now - as_of) < _LIVE_WINDOW

        sessions = active_sessions(as_of)
        session_state = SessionState(
            active_sessions=sessions, overlaps=session_overlaps(sessions)
        )

        as_of_str = self._as_of_string(as_of)
        timeframe_candles: dict[str, Candle] = {}
        for interval in TIMEFRAMES:
            row = fetch_latest_candle_at_or_before(self._conn, interval, as_of_str)
            if row is not None:
                timeframe_candles[interval] = Candle(
                    timestamp=row["timestamp"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"],
                )

        latest_price = spread = is_market_open = None
        if is_live:
            try:
                quote = self._client.get_quote()
                latest_price = quote["close"]
                is_market_open = quote["is_market_open"]
                # spread stays None: confirmed unavailable on the free tier.
            except TwelveDataError as exc:
                logger.warning(
                    "Live quote fetch failed, snapshot will omit price/market-open: %s", exc
                )

        return MarketDataSnapshot(
            as_of=as_of.isoformat(),
            is_live=is_live,
            latest_price=latest_price,
            spread=spread,
            is_market_open=is_market_open,
            sessions=session_state,
            timeframes=timeframe_candles,
        )
