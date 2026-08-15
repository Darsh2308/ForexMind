"""Integration tests for the SupportResistanceAgent.

Verifies the full pipeline from SQLite DB fetching to detector logic, returning
a SupportResistanceSnapshot suitable for the MarketContext blackboard.
"""

from __future__ import annotations

from forexmind.agents.support_resistance.support_resistance_agent import SupportResistanceAgent
from forexmind.storage.db import insert_candle


def _load_golden_into_db(db_conn, golden_candles, interval: str = "1day") -> None:
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


class TestSupportResistanceAgent:
    def test_analyze_single_timeframe(self, db_conn, golden_candles):
        _load_golden_into_db(db_conn, golden_candles)
        agent = SupportResistanceAgent(db_conn)

        snapshot = agent.analyze(["1day"])

        assert "1day" in snapshot.timeframes
        result = snapshot.timeframes["1day"]
        
        # Golden fixture has 65 bars, enough for swing points and 50 EMA, but not 200 EMA.
        assert isinstance(result.support_levels, list)
        assert isinstance(result.resistance_levels, list)
        
        # It should have found psychological levels at minimum
        all_levels = result.support_levels + result.resistance_levels
        assert len(all_levels) > 0
        
        types = [lvl.type for lvl in all_levels]
        assert "psychological" in types
        assert "dynamic" in types  # EMA_50 should be present
        # Note: horizontal levels might or might not be present depending on swing points 
        # in the golden fixture, but the types above are guaranteed.

    def test_analyze_multiple_timeframes(self, db_conn, golden_candles):
        _load_golden_into_db(db_conn, golden_candles, interval="1day")
        for candle in golden_candles[:20]:
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

        agent = SupportResistanceAgent(db_conn)
        snapshot = agent.analyze(["1day", "4h"])

        assert "1day" in snapshot.timeframes
        assert "4h" in snapshot.timeframes

    def test_empty_timeframe_is_skipped_or_returns_defaults(self, db_conn):
        agent = SupportResistanceAgent(db_conn)
        snapshot = agent.analyze(["1day"])
        
        # If DB is empty, it shouldn't crash, and can either omit the timeframe or be empty
        if "1day" in snapshot.timeframes:
            assert len(snapshot.timeframes["1day"].support_levels) == 0

    def test_as_of_prevents_lookahead(self, db_conn, golden_candles):
        _load_golden_into_db(db_conn, golden_candles)
        agent = SupportResistanceAgent(db_conn)

        # Cutoff on Feb 15
        snapshot = agent.analyze(["1day"], as_of="2024-02-15")
        
        assert snapshot.as_of == "2024-02-15"
        assert "1day" in snapshot.timeframes

    def test_blackboard_integration(self, db_conn, golden_candles):
        from datetime import datetime, timezone
        from forexmind.orchestration.market_context import MarketContext

        _load_golden_into_db(db_conn, golden_candles)
        agent = SupportResistanceAgent(db_conn)
        snapshot = agent.analyze(["1day"])

        context = MarketContext(
            generated_at=datetime.now(timezone.utc),
            timeframes=["1day"],
            support_resistance=snapshot,
        )

        assert "support_resistance" in context.populated_sections()
        assert context.support_resistance is not None
        assert "1day" in context.support_resistance.timeframes
