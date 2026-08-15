import csv
from pathlib import Path

import pytest

from forexmind.storage.db import get_connection, init_db

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def temp_db_path(tmp_path) -> Path:
    return tmp_path / "test_forexmind.db"


@pytest.fixture
def db_conn(temp_db_path):
    init_db(temp_db_path)
    conn = get_connection(temp_db_path)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def golden_candles() -> list[dict]:
    with (FIXTURES_DIR / "eurusd_sample.csv").open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append(
                {
                    "timestamp": row["timestamp"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]) if row["volume"] else None,
                }
            )
        return rows
