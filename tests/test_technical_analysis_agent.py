"""Integration tests for the TechnicalAnalysisAgent.

These test the full pipeline: golden fixture → SQLite → Agent → snapshot,
verifying the agent correctly wires the indicator computation to the database
and produces a well-formed TechnicalAnalysisSnapshot.
"""

from __future__ import annotations

from forexmind.agents.technical_analysis.technical_analysis_agent import (
    TechnicalAnalysisAgent,
)
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


class TestTechnicalAnalysisAgent:
    def test_analyze_single_timeframe(self, db_conn, golden_candles):
        """Agent produces a well-formed snapshot with the expected indicator
        values for the golden fixture."""
        _load_golden_into_db(db_conn, golden_candles)
        agent = TechnicalAnalysisAgent(db_conn)

        snapshot = agent.analyze(["1day"])

        assert "1day" in snapshot.timeframes
        indicators = snapshot.timeframes["1day"]
        # Sanity: key values should be populated (exact values tested
        # in test_indicators.py — here we verify the wiring).
        assert indicators.ema_20 is not None
        assert indicators.rsi_14 is not None
        assert indicators.macd_line is not None
        assert indicators.atr_14 is not None
        assert indicators.bb_upper is not None
        assert indicators.trend == "bullish"

    def test_analyze_multiple_timeframes(self, db_conn, golden_candles):
        """Each timeframe gets independent results."""
        _load_golden_into_db(db_conn, golden_candles, interval="1day")
        # Insert a small batch under a different interval
        for candle in golden_candles[:25]:
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

        agent = TechnicalAnalysisAgent(db_conn)
        snapshot = agent.analyze(["1day", "4h"])

        assert "1day" in snapshot.timeframes
        assert "4h" in snapshot.timeframes
        # 1day has 64 candles → EMA-50 available
        assert snapshot.timeframes["1day"].ema_50 is not None
        # 4h only has 25 candles → EMA-50 NOT available
        assert snapshot.timeframes["4h"].ema_50 is None

    def test_as_of_prevents_lookahead(self, db_conn, golden_candles):
        """With as_of set to a date in the middle of the fixture, only
        candles at or before that date should be used."""
        _load_golden_into_db(db_conn, golden_candles)
        agent = TechnicalAnalysisAgent(db_conn)

        # Use as_of = "2024-01-31" — only the first ~22 candles
        snapshot_early = agent.analyze(["1day"], as_of="2024-01-31")
        snapshot_full = agent.analyze(["1day"])

        early_ema = snapshot_early.timeframes["1day"].ema_20
        full_ema = snapshot_full.timeframes["1day"].ema_20

        # Both should exist (22 candles > 20 for EMA-20)
        assert early_ema is not None
        assert full_ema is not None
        # But they should differ since the data sets are different
        assert early_ema != full_ema

    def test_empty_timeframe_returns_empty_indicators(self, db_conn):
        """A timeframe with no candles should produce an IndicatorSet with
        all Nones, not raise."""
        agent = TechnicalAnalysisAgent(db_conn)

        snapshot = agent.analyze(["1day"])

        assert "1day" in snapshot.timeframes
        indicators = snapshot.timeframes["1day"]
        assert indicators.ema_20 is None
        assert indicators.rsi_14 is None
        assert indicators.trend == "neutral"

    def test_snapshot_as_of_is_set(self, db_conn, golden_candles):
        """The snapshot's as_of field should reflect the provided value."""
        _load_golden_into_db(db_conn, golden_candles)
        agent = TechnicalAnalysisAgent(db_conn)

        snapshot = agent.analyze(["1day"], as_of="2024-02-15")

        assert snapshot.as_of == "2024-02-15"

    def test_blackboard_integration(self, db_conn, golden_candles):
        """The snapshot should be assignable to MarketContext.technical_analysis."""
        from datetime import datetime, timezone

        from forexmind.orchestration.market_context import MarketContext

        _load_golden_into_db(db_conn, golden_candles)
        agent = TechnicalAnalysisAgent(db_conn)
        snapshot = agent.analyze(["1day"])

        context = MarketContext(
            generated_at=datetime.now(timezone.utc),
            timeframes=["1day"],
            technical_analysis=snapshot,
        )

        assert "technical_analysis" in context.populated_sections()
        assert context.technical_analysis.timeframes["1day"].ema_20 is not None
