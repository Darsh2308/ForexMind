import sqlite3
import pytest
import json
from datetime import datetime, timezone, timedelta
from forexmind.storage.db import init_db, insert_recommendation, insert_agent_snapshot
from forexmind.agents.learning.learning_agent import LearningAgent
from forexmind.orchestration.market_context import MarketContext
from forexmind.agents.market_data.schemas import MarketDataSnapshot, SessionState

@pytest.fixture
def mock_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    with open("forexmind/storage/schema.sql", "r", encoding="utf-8") as f:
        schema = f.read()
    conn.executescript(schema)
    yield conn
    conn.close()

def test_learning_agent_win_rate(mock_db):
    now = datetime.now(timezone.utc)
    
    # Create a dummy MarketContext that would map to segment "Neutral_Unknown"
    dummy_ctx = MarketContext(
        generated_at=now,
        symbol="EUR/USD"
    )
    payload = dummy_ctx.model_dump_json()
    
    # Insert 10 WINs within 30 days
    for _ in range(10):
        rec_id = insert_recommendation(mock_db, (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"), "BUY", status="WIN")
        insert_agent_snapshot(mock_db, rec_id, "market_context", payload, (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        
    # Insert 5 LOSSes within 30 days
    for _ in range(5):
        rec_id = insert_recommendation(mock_db, (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"), "BUY", status="LOSS")
        insert_agent_snapshot(mock_db, rec_id, "market_context", payload, (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"))

    # Total 30d: 15 trades, 10 wins -> WR = 0.66
    # Modifier = 0.66 - 0.50 = 0.16
    
    agent = LearningAgent(conn=mock_db)
    snapshot = agent.analyze(dummy_ctx)
    
    assert snapshot.segment_key == "Neutral_Unknown"
    assert snapshot.total_trades_analyzed == 15
    assert abs(snapshot.win_rate_30d - 0.666) < 0.01
    assert abs(snapshot.confidence_modifier - 0.17) < 0.01


def test_learning_agent_segment_key_with_active_session(mock_db):
    """Regression test: active_sessions is a list[str] (see
    market_data/schemas.py), not a list of enum members - accessing `.name`
    on one used to raise AttributeError for any context with a live session,
    i.e. almost every real market-hours call."""
    ctx = MarketContext(
        generated_at=datetime.now(timezone.utc),
        symbol="EUR/USD",
        market_data=MarketDataSnapshot(
            as_of="2026",
            is_live=True,
            sessions=SessionState(active_sessions=["London"], overlaps=[]),
        ),
    )

    agent = LearningAgent(conn=mock_db)
    snapshot = agent.analyze(ctx)

    assert snapshot.segment_key == "Neutral_London"
