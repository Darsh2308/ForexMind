"""Phase 1 exit-criteria demonstration: given a timestamp (or now, if none is
passed), reconstruct the multi-timeframe OHLC state at that moment.

Usage:
    python scripts/market_snapshot.py                      # live snapshot
    python scripts/market_snapshot.py 2026-07-20T12:00:00   # historical, as-of
"""

import logging
import sys
from datetime import datetime, timezone

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

    as_of = None
    if len(sys.argv) > 1:
        as_of = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc)

    init_db(config.db_path)
    conn = get_connection(config.db_path)
    client = TwelveDataClient(
        api_key=config.twelve_data_api_key,
        daily_request_limit=config.twelve_data_daily_request_limit,
    )
    agent = MarketDataAgent(client, conn)
    try:
        snapshot = agent.get_snapshot(as_of=as_of)
    finally:
        conn.close()

    print(snapshot.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
