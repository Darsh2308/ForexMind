"""Initializes the SQLite database at the configured DB_PATH from schema.sql.
Idempotent - safe to run repeatedly."""

from forexmind.config import load_config
from forexmind.logging_config import setup_logging
from forexmind.storage.db import init_db

import logging

setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    init_db(config.db_path)
    logger.info("Initialized database at %s", config.db_path)


if __name__ == "__main__":
    main()
