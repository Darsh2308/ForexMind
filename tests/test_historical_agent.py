import json
import sqlite3
import pytest
from datetime import datetime, timezone

from forexmind.storage.db import get_connection, init_db, insert_recommendation, insert_agent_snapshot
from forexmind.orchestration.market_context import MarketContext
from forexmind.agents.historical.historical_similarity_agent import HistoricalSimilarityAgent

@pytest.fixture
def memory_db():
    conn = get_connection(db_path=":memory:")
    # Initialize the schema directly for testing
    conn.executescript("""
        CREATE TABLE recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            recommendation TEXT,
            confidence REAL,
            entry REAL,
            stop_loss REAL,
            take_profit REAL,
            horizon TEXT,
            reasoning TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING'
        );
        CREATE TABLE agent_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_id INTEGER REFERENCES recommendations(id),
            agent_name TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    yield conn
    conn.close()

def build_mock_context(trend="bullish", rsi=20, smc_type="bullish OB", sr_dist=5, sr_type="support"):
    return MarketContext(
        generated_at=datetime.now(timezone.utc),
        symbol="EUR/USD",
        timeframes=["1h"],
        technical_analysis={
            "as_of": "2026-08-08T00:00:00+00:00",
            "timeframes": {"1h": {"trend": trend, "rsi_14": rsi}}
        },
        smc={
            "as_of": "2026-08-08T00:00:00+00:00",
            "timeframes": {"1h": {"pois": [{"type": smc_type}]}}
        },
        support_resistance={
            "as_of": "2026-08-08T00:00:00+00:00",
            "timeframes": {"1h": {"levels": [{"distance_pips": sr_dist, "level_type": sr_type}]}}
        }
    )

def test_historical_similarity(memory_db):
    # Insert a historical WIN setup that is heavily BULLISH
    hist_win_context = build_mock_context(trend="bullish", rsi=25, smc_type="bullish OB", sr_dist=2, sr_type="support")
    rec_id_win = insert_recommendation(memory_db, "2026-01-01T00:00:00Z", "BUY", status="WIN")
    insert_agent_snapshot(memory_db, rec_id_win, "market_context", hist_win_context.model_dump_json(), "2026-01-01T00:00:00Z")
    
    # Insert a historical LOSS setup that is heavily BEARISH
    hist_loss_context = build_mock_context(trend="bearish", rsi=80, smc_type="bearish OB", sr_dist=2, sr_type="resistance")
    rec_id_loss = insert_recommendation(memory_db, "2026-02-01T00:00:00Z", "SELL", status="LOSS")
    insert_agent_snapshot(memory_db, rec_id_loss, "market_context", hist_loss_context.model_dump_json(), "2026-02-01T00:00:00Z")

    agent = HistoricalSimilarityAgent(memory_db)
    
    # Analyze a current context identical to the WIN setup
    current_bullish_context = build_mock_context(trend="bullish", rsi=28, smc_type="bullish OB", sr_dist=4, sr_type="support")
    
    snapshot = agent.analyze(current_bullish_context)
    
    assert len(snapshot.top_similar) == 2
    
    # The WIN setup should have an extremely high similarity
    top_match = snapshot.top_similar[0]
    assert top_match.recommendation_id == rec_id_win
    assert top_match.similarity_score > 0.95
    assert top_match.historical_outcome == "WIN"
    
    # The LOSS setup should have a very low similarity
    bottom_match = snapshot.top_similar[1]
    assert bottom_match.recommendation_id == rec_id_loss
    assert bottom_match.similarity_score < 0.3
