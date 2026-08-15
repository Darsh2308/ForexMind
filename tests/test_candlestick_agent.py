"""Integration tests for the CandlestickAgent.

These test the full pipeline: golden fixture → SQLite → Agent → snapshot,
verifying the agent correctly wires pattern detection to the database and
produces a well-formed CandlestickSnapshot.
"""

from __future__ import annotations

from forexmind.agents.candlestick.candlestick_agent import CandlestickAgent
from forexmind.storage.db import insert_candle


def _load_golden_into_db(db_conn, golden_candles, interval: str = "1day") -> None:
    """Insert golden fixture candles into the test database."""
    for candle in golden_candles:
        insert_candle(
            db_conn,
            interval,
            candle["timestamp"],
            candle["open"],
            candle["high"],
            candle["low"],
            candle["close"],
            candle["volume"],
        )


class TestCandlestickAgent:
    def test_analyze_single_timeframe(self, db_conn, golden_candles):
        """Agent produces a well-formed snapshot from golden fixture data."""
        _load_golden_into_db(db_conn, golden_candles)
        agent = CandlestickAgent(db_conn)

        snapshot = agent.analyze(["1day"])

        assert "1day" in snapshot.timeframes
        # The golden fixture has 65 real EUR/USD daily candles — should
        # contain at least some patterns.
        patterns = snapshot.timeframes["1day"]
        assert isinstance(patterns, list)
        # Verify pattern objects have correct fields
        for p in patterns:
            assert p.name
            assert p.type in ("single", "multi")
            assert p.direction in ("bullish", "bearish", "neutral")
            assert p.candle_index >= 0
            assert p.timestamp

    def test_analyze_multiple_timeframes(self, db_conn, golden_candles):
        """Each timeframe gets independent results."""
        _load_golden_into_db(db_conn, golden_candles, interval="1day")
        # Insert a subset under a different interval
        for candle in golden_candles[:10]:
            insert_candle(
                db_conn,
                "4h",
                candle["timestamp"],
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
                candle["volume"],
            )

        agent = CandlestickAgent(db_conn)
        snapshot = agent.analyze(["1day", "4h"])

        assert "1day" in snapshot.timeframes
        assert "4h" in snapshot.timeframes

    def test_as_of_prevents_lookahead(self, db_conn, golden_candles):
        """With as_of set to a date in the middle, fewer candles are
        scanned so fewer (or different) patterns are detected."""
        _load_golden_into_db(db_conn, golden_candles)
        agent = CandlestickAgent(db_conn)

        snapshot_early = agent.analyze(["1day"], as_of="2024-01-31")
        snapshot_full = agent.analyze(["1day"])

        # Both should be valid
        assert "1day" in snapshot_early.timeframes
        assert "1day" in snapshot_full.timeframes
        # Early snapshot scans ~22 candles; full scans 65. They may differ.
        # At minimum, the early set should not exceed the full set in count
        # of patterns beyond the early date range.
        early_max_idx = max(
            (p.candle_index for p in snapshot_early.timeframes["1day"]),
            default=-1,
        )
        # All patterns in the early snapshot should have timestamps ≤ as_of
        for p in snapshot_early.timeframes["1day"]:
            assert p.timestamp <= "2024-01-31"

    def test_empty_timeframe_returns_empty(self, db_conn):
        """A timeframe with no candles produces an empty pattern list."""
        agent = CandlestickAgent(db_conn)

        snapshot = agent.analyze(["1day"])

        assert "1day" in snapshot.timeframes
        assert snapshot.timeframes["1day"] == []

    def test_snapshot_as_of_is_set(self, db_conn, golden_candles):
        """The snapshot's as_of field reflects the provided value."""
        _load_golden_into_db(db_conn, golden_candles)
        agent = CandlestickAgent(db_conn)

        snapshot = agent.analyze(["1day"], as_of="2024-02-15")
        assert snapshot.as_of == "2024-02-15"

    def test_blackboard_integration(self, db_conn, golden_candles):
        """The snapshot should be assignable to MarketContext.candlestick."""
        from datetime import datetime, timezone
        from forexmind.orchestration.market_context import MarketContext

        _load_golden_into_db(db_conn, golden_candles)
        agent = CandlestickAgent(db_conn)
        snapshot = agent.analyze(["1day"])

        context = MarketContext(
            generated_at=datetime.now(timezone.utc),
            timeframes=["1day"],
            candlestick=snapshot,
        )

        assert "candlestick" in context.populated_sections()
        assert isinstance(context.candlestick.timeframes["1day"], list)
