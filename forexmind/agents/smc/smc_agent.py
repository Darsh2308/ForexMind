from __future__ import annotations

import sqlite3
import pandas as pd

from forexmind.agents.smc.detectors import analyze_smc
from forexmind.agents.smc.schemas import SMCSnapshot
from forexmind.storage.db import fetch_candles, fetch_candles_before


class SMCAgent:
    """Agent 4: Identifies Smart Money Concepts.

    Reads OHLC data from the SQLite blackboard and outputs a structured list of
    FVGs, Order Blocks, Liquidity Pools, and Market Structure per timeframe.
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
    ) -> SMCSnapshot:
        """Run SMC detection across all provided timeframes.

        Args:
            timeframes: List of intervals to process (e.g., ["1day", "4h"]).
            as_of: Optional timestamp to prevent lookahead bias.

        Returns:
            A snapshot containing detected concepts for each timeframe.
        """
        snapshot = SMCSnapshot(as_of=as_of)

        for tf in timeframes:
            # We fetch more candles to ensure sufficient history for market structure
            if as_of is not None:
                rows = fetch_candles_before(self.db_conn, tf, as_of, limit=500)
            else:
                rows = fetch_candles(self.db_conn, tf)
                
            df = self._rows_to_dataframe(rows)
            if df.empty:
                continue

            result = analyze_smc(df)
            snapshot.timeframes[tf] = result

        return snapshot
