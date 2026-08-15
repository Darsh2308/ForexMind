"""Thin SQLite wrapper. No ORM - the schema is small and stable enough that
raw SQL is clearer than an abstraction layer would be."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    if str(db_path) != ":memory:":
        from pathlib import Path
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn = get_connection(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()


def insert_candle(
    conn: sqlite3.Connection,
    interval: str,
    timestamp: str,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO candles (interval, timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(interval, timestamp) DO UPDATE SET
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            volume = excluded.volume
        """,
        (interval, timestamp, open_, high, low, close, volume),
    )
    conn.commit()
    return cursor.lastrowid


def fetch_candles(conn: sqlite3.Connection, interval: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM candles WHERE interval = ? ORDER BY timestamp ASC",
        (interval,),
    ).fetchall()


def fetch_latest_candle_at_or_before(
    conn: sqlite3.Connection, interval: str, as_of: str
) -> sqlite3.Row | None:
    """The most recent candle for `interval` with timestamp <= `as_of`.

    `as_of` must be a UTC timestamp string in the same lexicographic format
    Twelve Data uses ("YYYY-MM-DD" for daily/weekly, "YYYY-MM-DD HH:MM:SS" for
    intraday) - both compare correctly as plain strings since one is always a
    prefix of the other for the same day. This is the lookahead-safe lookup:
    it never returns a candle that closes after `as_of`.
    """
    return conn.execute(
        """
        SELECT * FROM candles
        WHERE interval = ? AND timestamp <= ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (interval, as_of),
    ).fetchone()


def fetch_candles_before(
    conn: sqlite3.Connection, interval: str, as_of: str, limit: int = 500
) -> list[sqlite3.Row]:
    """Return up to `limit` candles for `interval` with timestamp <= `as_of`,
    ordered **oldest-first** (chronological).

    This is the lookahead-safe bulk query used by the Technical Analysis
    Agent to feed indicator computations that need a lookback window of
    historical data without ever seeing future candles.
    """
    return conn.execute(
        """
        SELECT * FROM candles
        WHERE interval = ? AND timestamp <= ?
        ORDER BY timestamp ASC
        LIMIT ?
        """,
        (interval, as_of, limit),
    ).fetchall()


def fetch_candles_after(
    conn: sqlite3.Connection, interval: str, as_of: str, limit: int = 1000
) -> list[sqlite3.Row]:
    """Return up to `limit` candles for `interval` with timestamp > `as_of`,
    ordered **oldest-first** (chronological).
    Used by the Evaluation Agent to sweep price action and detect SL/TP hits.
    """
    return conn.execute(
        """
        SELECT * FROM candles
        WHERE interval = ? AND timestamp > ?
        ORDER BY timestamp ASC
        LIMIT ?
        """,
        (interval, as_of, limit),
    ).fetchall()


def insert_recommendation(
    conn: sqlite3.Connection,
    created_at: str,
    recommendation: str,
    confidence: float | None = None,
    entry: float | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    horizon: str | None = None,
    reasoning: str | None = None,
    status: str = "PENDING"
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO recommendations 
        (created_at, recommendation, confidence, entry, stop_loss, take_profit, horizon, reasoning, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (created_at, recommendation, confidence, entry, stop_loss, take_profit, horizon, reasoning, status)
    )
    conn.commit()
    return cursor.lastrowid


def insert_agent_snapshot(
    conn: sqlite3.Connection,
    recommendation_id: int,
    agent_name: str,
    payload: str,
    created_at: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO agent_snapshots
        (recommendation_id, agent_name, payload, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (recommendation_id, agent_name, payload, created_at)
    )
    conn.commit()
    return cursor.lastrowid


def fetch_historical_setups(conn: sqlite3.Connection, limit: int = 500) -> list[sqlite3.Row]:
    """Fetches past recommendations that have been resolved (WIN/LOSS) with their market_context payload."""
    return conn.execute(
        """
        SELECT r.id as recommendation_id, r.status, r.created_at, s.payload as market_context_json
        FROM recommendations r
        JOIN agent_snapshots s ON r.id = s.recommendation_id
        WHERE s.agent_name = 'market_context' AND r.status IN ('WIN', 'LOSS')
        ORDER BY r.created_at DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()

def fetch_resolved_recommendations(conn: sqlite3.Connection, since_timestamp: str | None = None) -> list[sqlite3.Row]:
    """Fetches resolved recommendations (WIN/LOSS) and their payloads.
    If since_timestamp is provided, only fetches records created after it.
    """
    query = """
        SELECT r.id as recommendation_id, r.status, r.created_at, s.payload as market_context_json
        FROM recommendations r
        JOIN agent_snapshots s ON r.id = s.recommendation_id
        WHERE s.agent_name = 'market_context' AND r.status IN ('WIN', 'LOSS')
    """
    params = []
    
    if since_timestamp:
        query += " AND r.created_at >= ?"
        params.append(since_timestamp)
        
    query += " ORDER BY r.created_at DESC"
    
    return conn.execute(query, params).fetchall()

def fetch_pending_recommendations(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Fetches all recommendations that are currently PENDING."""
    return conn.execute(
        "SELECT * FROM recommendations WHERE status = 'PENDING' ORDER BY created_at ASC"
    ).fetchall()

def fetch_all_recommendations(conn: sqlite3.Connection, limit: int = 50) -> list[sqlite3.Row]:
    """Fetches recommendation history for the API endpoint."""
    return conn.execute(
        "SELECT * FROM recommendations ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()

def update_recommendation_status(conn: sqlite3.Connection, rec_id: int, status: str) -> None:
    """Updates the status of a recommendation (e.g. to WIN, LOSS, or EXPIRED)."""
    conn.execute(
        "UPDATE recommendations SET status = ? WHERE id = ?",
        (status, rec_id)
    )
    conn.commit()
