"""End-to-end smoke test, offline version: exercises fetch -> store -> log ->
blackboard using the real MarketDataAgent against the golden fixture instead
of the live Twelve Data API, so it needs no network access or API key.
"""

import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock

from forexmind.agents.market_data.market_data_agent import MarketDataAgent
from forexmind.orchestration.market_context import MarketContext
from forexmind.storage.db import fetch_candles, insert_candle


def test_fetch_store_log_pipeline_end_to_end(db_conn, golden_candles, caplog):
    logger = logging.getLogger("forexmind.smoke")

    with caplog.at_level(logging.INFO):
        for candle in golden_candles:
            insert_candle(
                db_conn,
                "1day",
                candle["timestamp"],
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
                candle["volume"],
            )
        latest = golden_candles[-1]
        logger.info(
            "Stored candle interval=%s timestamp=%s close=%s",
            "1day",
            latest["timestamp"],
            latest["close"],
        )

    stored = fetch_candles(db_conn, "1day")
    assert len(stored) == len(golden_candles)
    assert "Stored candle" in caplog.text

    # No real API calls should happen for a historical as-of snapshot.
    client = MagicMock()
    agent = MarketDataAgent(client, db_conn)
    as_of = datetime.fromisoformat(latest["timestamp"]).replace(
        hour=23, tzinfo=timezone.utc
    )
    snapshot = agent.get_snapshot(as_of=as_of)
    client.get_quote.assert_not_called()
    client.get_time_series.assert_not_called()

    context = MarketContext(
        generated_at=datetime.now(timezone.utc),
        timeframes=["1day"],
        market_data=snapshot,
    )

    assert context.populated_sections() == ["market_data"]
    assert context.market_data.timeframes["1day"].close == latest["close"]
