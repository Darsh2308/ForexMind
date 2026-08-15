from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from forexmind.agents.market_data.market_data_agent import MarketDataAgent
from forexmind.agents.market_data.twelve_data_client import TwelveDataError
from forexmind.storage.db import insert_candle


def _fake_client(time_series_return=None, quote_return=None, quote_side_effect=None):
    client = MagicMock()
    client.get_time_series.return_value = time_series_return or []
    if quote_side_effect is not None:
        client.get_quote.side_effect = quote_side_effect
    else:
        client.get_quote.return_value = quote_return or {
            "close": 1.13684,
            "is_market_open": True,
        }
    return client


def test_backfill_timeframe_stores_all_returned_candles(db_conn):
    client = _fake_client(
        time_series_return=[
            {"timestamp": "2026-07-25", "open": 1.1, "high": 1.11, "low": 1.09, "close": 1.105, "volume": None},
            {"timestamp": "2026-07-24", "open": 1.09, "high": 1.10, "low": 1.08, "close": 1.10, "volume": None},
        ]
    )
    agent = MarketDataAgent(client, db_conn)

    count = agent.backfill_timeframe("1day", outputsize=500)

    assert count == 2
    rows = db_conn.execute("SELECT * FROM candles WHERE interval = '1day'").fetchall()
    assert len(rows) == 2


def test_backfill_all_timeframes_continues_after_one_failure(db_conn):
    client = _fake_client()
    client.get_time_series.side_effect = [
        TwelveDataError("boom"),
        [{"timestamp": "2026-07-25", "open": 1.1, "high": 1.11, "low": 1.09, "close": 1.105, "volume": None}],
    ] + [[] for _ in range(10)]
    agent = MarketDataAgent(client, db_conn)

    results = agent.backfill_all_timeframes(outputsize=10)

    assert results["1min"] == 0
    assert results["5min"] == 1


def test_historical_snapshot_never_leaks_future_candles(db_conn):
    """The core Phase 1 exit criterion: as-of reconstruction must not see
    candles that close after the requested timestamp."""
    client = _fake_client()
    agent = MarketDataAgent(client, db_conn)

    insert_candle(db_conn, "1day", "2026-07-24", 1.09, 1.10, 1.08, 1.10)
    insert_candle(db_conn, "1day", "2026-07-25", 1.10, 1.11, 1.09, 1.105)
    insert_candle(db_conn, "1day", "2026-07-26", 1.105, 1.12, 1.10, 1.11)

    as_of = datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc)
    snapshot = agent.get_snapshot(as_of=as_of)

    assert snapshot.is_live is False
    assert snapshot.timeframes["1day"].timestamp == "2026-07-25"
    assert snapshot.latest_price is None
    client.get_quote.assert_not_called()


def test_historical_snapshot_before_any_data_omits_timeframe(db_conn):
    client = _fake_client()
    agent = MarketDataAgent(client, db_conn)
    insert_candle(db_conn, "1day", "2026-07-25", 1.10, 1.11, 1.09, 1.105)

    snapshot = agent.get_snapshot(as_of=datetime(2020, 1, 1, tzinfo=timezone.utc))

    assert "1day" not in snapshot.timeframes


def test_live_snapshot_calls_quote_and_fills_price(db_conn):
    client = _fake_client(quote_return={"close": 1.1368, "is_market_open": True})
    agent = MarketDataAgent(client, db_conn)
    insert_candle(db_conn, "15min", "2026-07-26 15:00:00", 1.136, 1.137, 1.135, 1.1368)

    snapshot = agent.get_snapshot(as_of=datetime.now(timezone.utc))

    assert snapshot.is_live is True
    assert snapshot.latest_price == 1.1368
    assert snapshot.is_market_open is True
    assert snapshot.spread is None  # confirmed unavailable on free tier


def test_live_snapshot_degrades_gracefully_on_quote_failure(db_conn):
    client = _fake_client(quote_side_effect=TwelveDataError("rate limited"))
    agent = MarketDataAgent(client, db_conn)

    snapshot = agent.get_snapshot(as_of=datetime.now(timezone.utc))

    assert snapshot.is_live is True
    assert snapshot.latest_price is None


def test_sessions_are_populated_for_any_as_of(db_conn):
    client = _fake_client()
    agent = MarketDataAgent(client, db_conn)

    snapshot = agent.get_snapshot(as_of=datetime(2026, 7, 25, 8, 0, tzinfo=timezone.utc))

    assert set(snapshot.sessions.active_sessions) == {"Tokyo", "London"}
    assert snapshot.sessions.overlaps == ["Tokyo-London"]


def test_snapshot_just_outside_live_window_is_not_live(db_conn):
    client = _fake_client()
    agent = MarketDataAgent(client, db_conn)

    just_old_enough = datetime.now(timezone.utc) - timedelta(minutes=2)
    snapshot = agent.get_snapshot(as_of=just_old_enough)

    assert snapshot.is_live is False
    client.get_quote.assert_not_called()
