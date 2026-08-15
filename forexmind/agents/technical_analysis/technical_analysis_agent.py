"""Agent 2: Technical Analysis Agent.

Deterministic indicator computation — no LLM. Reads OHLC candle data from
SQLite (put there by the Market Data Agent in Phase 1), computes indicators
via the pure functions in ``indicators.py``, and writes a structured
``TechnicalAnalysisSnapshot`` onto the blackboard.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

import pandas as pd

from forexmind.agents.technical_analysis.indicators import compute_indicators
from forexmind.agents.technical_analysis.schemas import (
    IndicatorSet,
    TechnicalAnalysisSnapshot,
)
from forexmind.storage.db import fetch_candles, fetch_candles_before

logger = logging.getLogger(__name__)


class TechnicalAnalysisAgent:
    """Computes technical indicators for one or more timeframes.

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
        columns the indicator functions expect."""
        if not rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])
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
        # Ensure chronological order (oldest first) — required for all
        # indicator computations that depend on sequential lookback.
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def analyze_timeframe(
        self, interval: str, as_of: str | None = None
    ) -> IndicatorSet:
        """Compute indicators for a single timeframe.

        Parameters
        ----------
        interval : str
            The candle interval (e.g. "1day", "4h", "15min").
        as_of : str, optional
            UTC timestamp string. If provided, only candles with
            ``timestamp <= as_of`` are used — preventing lookahead.
            If None, all stored candles are used.
        """
        if as_of is not None:
            rows = fetch_candles_before(self._conn, interval, as_of)
        else:
            rows = fetch_candles(self._conn, interval)

        df = self._rows_to_dataframe(rows)
        if df.empty:
            logger.info(
                "No candles found for interval=%s as_of=%s — returning empty IndicatorSet",
                interval,
                as_of,
            )
            return IndicatorSet()

        logger.info(
            "Computing indicators for interval=%s with %d candles (as_of=%s)",
            interval,
            len(df),
            as_of or "latest",
        )
        return compute_indicators(df)

    def analyze(
        self,
        timeframes: list[str],
        as_of: str | None = None,
    ) -> TechnicalAnalysisSnapshot:
        """Compute indicators for multiple timeframes.

        Parameters
        ----------
        timeframes : list[str]
            Intervals to analyse (e.g. ["15min", "1h", "4h", "1day"]).
        as_of : str, optional
            Lookahead-safe cutoff — see ``analyze_timeframe``.

        Returns
        -------
        TechnicalAnalysisSnapshot
            A snapshot containing an ``IndicatorSet`` per timeframe.
        """
        now_str = as_of or datetime.now(timezone.utc).isoformat()
        result: dict[str, IndicatorSet] = {}
        for interval in timeframes:
            result[interval] = self.analyze_timeframe(interval, as_of=as_of)
        return TechnicalAnalysisSnapshot(as_of=now_str, timeframes=result)
