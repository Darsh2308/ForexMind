"""Agent 5: Candlestick Agent.

Deterministic candlestick-pattern detection — no LLM.  Reads OHLC candle
data from SQLite (put there by the Market Data Agent in Phase 1), runs all
pattern detectors via ``patterns.py``, and writes a structured
``CandlestickSnapshot`` onto the blackboard.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

import pandas as pd

from forexmind.agents.candlestick.patterns import detect_all_patterns
from forexmind.agents.candlestick.schemas import (
    CandlestickPattern,
    CandlestickSnapshot,
)
from forexmind.storage.db import fetch_candles, fetch_candles_before

logger = logging.getLogger(__name__)


class CandlestickAgent:
    """Detects candlestick patterns for one or more timeframes.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection with the ``candles`` table populated
        (typically by the Market Data Agent's backfill step).
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _rows_to_dataframe(self, rows: list) -> pd.DataFrame:
        """Convert sqlite3.Row results into a pandas DataFrame with the
        columns the pattern detectors expect."""
        if not rows:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close"]
            )
        records = [
            {
                "timestamp": row["timestamp"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
            for row in rows
        ]
        df = pd.DataFrame(records)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def analyze_timeframe(
        self, interval: str, as_of: str | None = None
    ) -> list[CandlestickPattern]:
        """Detect patterns for a single timeframe.

        Parameters
        ----------
        interval : str
            The candle interval (e.g. ``"1day"``, ``"4h"``, ``"15min"``).
        as_of : str, optional
            UTC timestamp string.  If provided, only candles with
            ``timestamp <= as_of`` are used — preventing lookahead.
        """
        if as_of is not None:
            rows = fetch_candles_before(self._conn, interval, as_of)
        else:
            rows = fetch_candles(self._conn, interval)

        df = self._rows_to_dataframe(rows)
        if df.empty:
            logger.info(
                "No candles found for interval=%s as_of=%s — returning empty patterns",
                interval,
                as_of,
            )
            return []

        logger.info(
            "Detecting candlestick patterns for interval=%s with %d candles (as_of=%s)",
            interval,
            len(df),
            as_of or "latest",
        )
        return detect_all_patterns(df)

    def analyze(
        self,
        timeframes: list[str],
        as_of: str | None = None,
    ) -> CandlestickSnapshot:
        """Detect patterns for multiple timeframes.

        Parameters
        ----------
        timeframes : list[str]
            Intervals to analyse (e.g. ``["15min", "1h", "4h", "1day"]``).
        as_of : str, optional
            Lookahead-safe cutoff — see ``analyze_timeframe``.

        Returns
        -------
        CandlestickSnapshot
            A snapshot containing detected patterns per timeframe.
        """
        now_str = as_of or datetime.now(timezone.utc).isoformat()
        result: dict[str, list[CandlestickPattern]] = {}
        for interval in timeframes:
            result[interval] = self.analyze_timeframe(interval, as_of=as_of)
        return CandlestickSnapshot(as_of=now_str, timeframes=result)
