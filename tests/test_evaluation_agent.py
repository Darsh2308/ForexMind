import sqlite3
import pytest
from forexmind.storage.db import init_db, insert_recommendation, insert_candle
from forexmind.agents.evaluation.evaluation_agent import EvaluationAgent

@pytest.fixture
def mock_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Read schema directly
    with open("forexmind/storage/schema.sql", "r", encoding="utf-8") as f:
        schema = f.read()
    conn.executescript(schema)
    yield conn
    conn.close()

def test_evaluation_agent_win(mock_db):
    # Insert a BUY recommendation
    rec_id = insert_recommendation(
        conn=mock_db,
        created_at="2026-08-08T10:00:00Z",
        recommendation="BUY",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        status="PENDING"
    )
    
    # Insert candles after created_at
    # Candle 1: Doesn't hit anything (Low: 1.0980, High: 1.1050)
    insert_candle(mock_db, "15min", "2026-08-08T10:15:00Z", 1.1000, 1.1050, 1.0980, 1.1020)
    # Candle 2: Hits TP (High: 1.1150 > 1.1100)
    insert_candle(mock_db, "15min", "2026-08-08T10:30:00Z", 1.1020, 1.1150, 1.1010, 1.1120)
    
    agent = EvaluationAgent(conn=mock_db)
    agent.evaluate_all(current_time="2026-08-08T11:00:00Z")
    
    # Verify status changed to WIN
    row = mock_db.execute("SELECT status FROM recommendations WHERE id = ?", (rec_id,)).fetchone()
    assert row["status"] == "WIN"

def test_evaluation_agent_loss(mock_db):
    # Insert a SELL recommendation
    rec_id = insert_recommendation(
        conn=mock_db,
        created_at="2026-08-08T10:00:00Z",
        recommendation="SELL",
        entry=1.1000,
        stop_loss=1.1050,
        take_profit=1.0900,
        status="PENDING"
    )
    
    # Insert candles
    # Candle 1: Hits SL (High: 1.1080 > 1.1050)
    insert_candle(mock_db, "15min", "2026-08-08T10:15:00Z", 1.1000, 1.1080, 1.0980, 1.1050)
    
    agent = EvaluationAgent(conn=mock_db)
    agent.evaluate_all(current_time="2026-08-08T11:00:00Z")
    
    # Verify status changed to LOSS
    row = mock_db.execute("SELECT status FROM recommendations WHERE id = ?", (rec_id,)).fetchone()
    assert row["status"] == "LOSS"
