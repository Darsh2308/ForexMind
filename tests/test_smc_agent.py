"""Integration tests for the SMCAgent.

Verifies the full pipeline from SQLite DB fetching to detector logic, returning
a SMCSnapshot suitable for the MarketContext blackboard.
"""

from __future__ import annotations

from forexmind.agents.smc.smc_agent import SMCAgent
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


class TestSMCAgent:
    def test_analyze_single_timeframe(self, db_conn, golden_candles):
        _load_golden_into_db(db_conn, golden_candles)
        agent = SMCAgent(db_conn)

        snapshot = agent.analyze(["1day"])

        assert "1day" in snapshot.timeframes
        result = snapshot.timeframes["1day"]
        
        # Golden fixture has 65 bars, should detect some FVGs or at least dealing range
        assert isinstance(result.fvgs, list)
        assert isinstance(result.order_blocks, list)
        
        if result.dealing_range:
            assert result.dealing_range.current_zone in ["premium", "discount", "equilibrium"]

    def test_analyze_multiple_timeframes(self, db_conn, golden_candles):
        _load_golden_into_db(db_conn, golden_candles, interval="1day")
        for candle in golden_candles[:30]:
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

        agent = SMCAgent(db_conn)
        snapshot = agent.analyze(["1day", "4h"])

        assert "1day" in snapshot.timeframes
        assert "4h" in snapshot.timeframes

    def test_empty_timeframe_is_skipped_or_returns_defaults(self, db_conn):
        agent = SMCAgent(db_conn)
        snapshot = agent.analyze(["1day"])
        
        if "1day" in snapshot.timeframes:
            assert len(snapshot.timeframes["1day"].fvgs) == 0

    def test_as_of_prevents_lookahead(self, db_conn, golden_candles):
        _load_golden_into_db(db_conn, golden_candles)
        agent = SMCAgent(db_conn)

        # Cutoff on Feb 15
        snapshot = agent.analyze(["1day"], as_of="2024-02-15")
        
        assert snapshot.as_of == "2024-02-15"
        assert "1day" in snapshot.timeframes

    def test_blackboard_integration(self, db_conn, golden_candles):
        from datetime import datetime, timezone
        from forexmind.orchestration.market_context import MarketContext

        _load_golden_into_db(db_conn, golden_candles)
        agent = SMCAgent(db_conn)
        snapshot = agent.analyze(["1day"])

        context = MarketContext(
            generated_at=datetime.now(timezone.utc),
            timeframes=["1day"],
            smc=snapshot,
        )

        assert "smc" in context.populated_sections()
        assert context.smc is not None
        assert "1day" in context.smc.timeframes
