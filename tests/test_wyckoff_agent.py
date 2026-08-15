import sqlite3
import pandas as pd
import pytest

from forexmind.agents.wyckoff.wyckoff_agent import WyckoffAgent


@pytest.fixture
def empty_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE candles (
            symbol TEXT,
            interval TEXT,
            timestamp TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            UNIQUE(symbol, interval, timestamp)
        )
        """
    )
    conn.commit()
    return conn


def test_wyckoff_agent_empty_db(empty_db):
    agent = WyckoffAgent(empty_db)
    res = agent.analyze(["1day"])
    assert "1day" in res.timeframes
    assert res.timeframes["1day"].current_phase.phase == "unknown"
