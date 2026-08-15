"""Phase 0 end-to-end smoke script: fetch one live EUR/USD daily candle from
Twelve Data, store it in SQLite, log the result.

Requires TWELVE_DATA_API_KEY to be set in .env (see .env.example). Without a
real key this exits with a clear message instead of failing obscurely -
Phase 0's offline tests (tests/test_smoke_pipeline.py) already cover the
store+log half of this flow against fixture data.
"""

import logging
import sys

from forexmind.agents.market_data.twelve_data_client import (
    TwelveDataClient,
    TwelveDataError,
)
from forexmind.config import load_config
from forexmind.logging_config import setup_logging
from forexmind.storage.db import init_db, insert_candle, get_connection

setup_logging()
logger = logging.getLogger(__name__)


def main() -> int:
    config = load_config()
    if not config.has_twelve_data_key:
        logger.warning(
            "TWELVE_DATA_API_KEY is not set. Copy .env.example to .env and add a "
            "free key from https://twelvedata.com, then re-run this script."
        )
        return 1

    init_db(config.db_path)
    client = TwelveDataClient(
        api_key=config.twelve_data_api_key,
        daily_request_limit=config.twelve_data_daily_request_limit,
    )

    try:
        candles = client.get_time_series(interval="1day", outputsize=1)
    except TwelveDataError as exc:
        logger.error("Failed to fetch candle from Twelve Data: %s", exc)
        return 1

    if not candles:
        logger.error("Twelve Data returned no candles.")
        return 1

    candle = candles[0]
    conn = get_connection(config.db_path)
    try:
        insert_candle(
            conn,
            "1day",
            candle["timestamp"],
            candle["open"],
            candle["high"],
            candle["low"],
            candle["close"],
            candle["volume"],
        )
    finally:
        conn.close()

    logger.info(
        "Stored candle interval=1day timestamp=%s close=%s",
        candle["timestamp"],
        candle["close"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
