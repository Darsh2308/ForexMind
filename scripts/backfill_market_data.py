"""Phase 1: backfills historical OHLC for every configured timeframe
(1min/5min/15min/30min/1h/4h/1day/1week) into SQLite."""

import logging
import sys

from forexmind.agents.market_data.market_data_agent import MarketDataAgent
from forexmind.agents.market_data.twelve_data_client import TwelveDataClient
from forexmind.config import load_config
from forexmind.logging_config import setup_logging
from forexmind.storage.db import get_connection, init_db

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
    conn = get_connection(config.db_path)
    client = TwelveDataClient(
        api_key=config.twelve_data_api_key,
        daily_request_limit=config.twelve_data_daily_request_limit,
    )
    agent = MarketDataAgent(client, conn)

    try:
        results = agent.backfill_all_timeframes(outputsize=500)
    finally:
        conn.close()

    logger.info("Backfill complete: %s", results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
