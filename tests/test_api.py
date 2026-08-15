import pytest
from fastapi.testclient import TestClient
from forexmind.api.app import app
from unittest.mock import patch, MagicMock

# We use the standard TestClient from FastAPI
client = TestClient(app)

def test_history_endpoint_empty():
    with patch("forexmind.api.app.fetch_all_recommendations", return_value=[]):
        response = client.get("/api/history")
        assert response.status_code == 200
        assert response.json() == {"recommendations": []}

def test_history_endpoint_with_data():
    mock_rows = [
        {
            "id": 1,
            "created_at": "2026-08-08T10:00:00Z",
            "recommendation": "BUY",
            "entry": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1100,
            "status": "WIN"
        }
    ]
    
    with patch("forexmind.api.app.fetch_all_recommendations", return_value=mock_rows):
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["status"] == "WIN"

@patch("forexmind.api.app.graph")
def test_analyze_endpoint(mock_graph):
    # Mock the return value of graph.invoke
    from forexmind.orchestration.market_context import MarketContext
    from forexmind.agents.reasoning.schemas import ReasoningSnapshot
    from datetime import datetime, timezone
    
    ctx = MarketContext(symbol="EUR/USD", generated_at=datetime.now(timezone.utc))
    ctx.reasoning_output = ReasoningSnapshot(
        recommendation="BUY",
        confidence=0.8,
        entry=1.1,
        stop_loss=1.09,
        take_profit=1.12,
        reasoning="Test reasoning",
        supporting_evidence=[],
        conflicting_evidence=[],
        important_news=[],
        trade_quality_score=9
    )
    
    mock_graph.invoke.return_value = {"market_context": ctx}
    
    # We also need to patch DB operations in the endpoint since it opens a real SQLite DB
    with patch("forexmind.api.app.get_connection"):
        response = client.post("/api/analyze", json={"symbol": "EUR/USD"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "EUR/USD"
        assert data["recommendation"]["recommendation"] == "BUY"
        assert data["recommendation"]["confidence"] == 0.8
