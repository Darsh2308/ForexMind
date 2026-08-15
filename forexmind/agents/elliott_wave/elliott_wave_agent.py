"""Agent 7: Elliott Wave Agent.

Probabilistic/subjective analysis for Elliott Wave patterns.
Outputs an advisory signal and a confidence score.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

import pandas as pd

from forexmind.agents.elliott_wave.detectors import analyze_elliott_wave
from forexmind.agents.elliott_wave.schemas import (
    ElliottWaveResult,
    ElliottWaveSnapshot,
)
from forexmind.storage.db import fetch_candles, fetch_candles_before

logger = logging.getLogger(__name__)


class ElliottWaveAgent:
    """Analyzes Elliott Wave patterns for one or more timeframes."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _rows_to_dataframe(self, rows: list) -> pd.DataFrame:
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
    ) -> ElliottWaveResult:
        if as_of is not None:
            rows = fetch_candles_before(self._conn, interval, as_of)
        else:
            rows = fetch_candles(self._conn, interval)

        df = self._rows_to_dataframe(rows)
        if df.empty:
            return ElliottWaveResult()

        logger.info(
            "Analysing Elliott Wave for interval=%s with %d candles (as_of=%s)",
            interval,
            len(df),
            as_of or "latest",
        )
        return analyze_elliott_wave(df)

    def analyze(
        self,
        timeframes: list[str],
        as_of: str | None = None,
    ) -> ElliottWaveSnapshot:
        now_str = as_of or datetime.now(timezone.utc).isoformat()
        result: dict[str, ElliottWaveResult] = {}
        for interval in timeframes:
            result[interval] = self.analyze_timeframe(interval, as_of=as_of)
        return ElliottWaveSnapshot(as_of=now_str, timeframes=result)
