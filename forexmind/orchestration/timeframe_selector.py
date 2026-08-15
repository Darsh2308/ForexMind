from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from forexmind.agents.market_data.sessions import active_sessions
from forexmind.agents.technical_analysis.technical_analysis_agent import TechnicalAnalysisAgent
from forexmind.storage.db import fetch_latest_candle_at_or_before


def _as_of_string(as_of: datetime) -> str:
    """Matches Twelve Data's UTC timestamp format."""
    return as_of.strftime("%Y-%m-%d %H:%M:%S")


def select_timeframes(conn: sqlite3.Connection, as_of: str | None = None) -> list[str]:
    """
    Determines the most appropriate timeframe combination based on current market volatility and session overlaps.
    
    Parameters
    ----------
    conn : sqlite3.Connection
        An open database connection.
    as_of : str, optional
        UTC timestamp string (ISO format). If None, current UTC time is used.

    Returns
    -------
    list[str]
        A list of timeframes (e.g., ["15min", "1h", "4h"]) the agents should run against.
    """
    now = datetime.now(timezone.utc)
    if as_of:
        dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = now

    sessions = active_sessions(dt)
    is_high_activity_session = ("London" in sessions and "New York" in sessions)
    
    is_low_activity_session = (
        not is_high_activity_session
        and ("Sydney" in sessions or "Tokyo" in sessions)
        and ("London" not in sessions)
        and ("New York" not in sessions)
    )

    db_as_of = _as_of_string(dt)

    # Measure volatility
    ta_agent = TechnicalAnalysisAgent(conn)
    # Using 1day for a stable ATR reading
    ta_snapshot = ta_agent.analyze_timeframe("1day", as_of=db_as_of)
    
    latest_candle = fetch_latest_candle_at_or_before(conn, "1day", db_as_of)
    
    normalized_atr = 0.0
    if latest_candle and ta_snapshot.atr_14:
        close_price = float(latest_candle["close"])
        if close_price > 0:
            normalized_atr = ta_snapshot.atr_14 / close_price

    # High volatility threshold for EUR/USD (e.g., 0.0060 is ~60 pips on a 1.0000 base)
    HIGH_VOLATILITY_THRESHOLD = 0.0060
    is_high_volatility = normalized_atr >= HIGH_VOLATILITY_THRESHOLD

    # Classification Rules
    if is_high_volatility or is_high_activity_session:
        # Scalping / Fast Intraday
        return ["5min", "15min", "1h", "4h"]
    elif is_low_activity_session and not is_high_volatility:
        # Swing / Context
        return ["1h", "4h", "1day"]
    else:
        # Intraday
        return ["15min", "1h", "4h"]
