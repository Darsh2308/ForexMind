from __future__ import annotations

import sqlite3

from forexmind.agents.support_resistance.detectors import analyze_support_resistance
from forexmind.agents.support_resistance.schemas import SupportResistanceSnapshot
from forexmind.storage.db import fetch_candles, fetch_candles_before
import pandas as pd

class SupportResistanceAgent:
    """Agent 6: Identifies horizontal, psychological, and dynamic S/R levels.

    Reads OHLC data from the SQLite blackboard and outputs a structured list of
    support and resistance levels per timeframe.
    """

    def __init__(self, db_conn: sqlite3.Connection):
        self.db_conn = db_conn

    def _rows_to_dataframe(self, rows: list) -> pd.DataFrame:
        """Convert sqlite3.Row results into a pandas DataFrame."""
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
        return pd.DataFrame(records)

    def analyze(
        self, timeframes: list[str], as_of: str | None = None
    ) -> SupportResistanceSnapshot:
        """Run Support & Resistance detection across all provided timeframes.

        Args:
            timeframes: List of intervals to process (e.g., ["1day", "4h"]).
            as_of: Optional timestamp to prevent lookahead bias.

        Returns:
            A snapshot containing detected levels for each timeframe.
        """
        snapshot = SupportResistanceSnapshot(as_of=as_of)

        for tf in timeframes:
            # We fetch more candles to ensure 200 EMA can calculate and
            # enough history exists for robust horizontal level clustering.
            if as_of is not None:
                rows = fetch_candles_before(self.db_conn, tf, as_of, limit=300)
            else:
                rows = fetch_candles(self.db_conn, tf)
                
            df = self._rows_to_dataframe(rows)
            if df.empty:
                continue

            result = analyze_support_resistance(df)
            snapshot.timeframes[tf] = result

        return snapshot
