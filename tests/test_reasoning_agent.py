import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from forexmind.orchestration.market_context import MarketContext
from forexmind.agents.reasoning.reasoning_agent import ReasoningAgent
from forexmind.agents.reasoning.schemas import ReasoningSnapshot

@pytest.fixture
def mock_context():
    return MarketContext(
        generated_at=datetime.now(timezone.utc),
        symbol="EUR/USD",
        timeframes=["1h"]
    )

def test_reasoning_agent_invocation(mock_context):
    agent = ReasoningAgent(api_key="dummy")
    
    mock_snapshot = ReasoningSnapshot(
        recommendation="BUY",
        confidence=0.85,
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        reasoning="Market structure is highly bullish and R:R is favorable.",
        supporting_evidence=["Bullish OB", "Uptrend on 1H"],
        conflicting_evidence=["Minor resistance nearby"],
        historical_similarity=0.92,
        reward_to_risk=3.0,
        important_news=["Fed rate cut expectations"],
        trade_quality_score=8
    )
    
    agent.structured_llm = MagicMock()
    agent.structured_llm.invoke.return_value = mock_snapshot
    
    result = agent.analyze(mock_context)
    
    # Verify the LLM was invoked
    agent.structured_llm.invoke.assert_called_once()
    
    # Verify result matches
    assert result.recommendation == "BUY"
    assert result.confidence == 0.85
    assert result.trade_quality_score == 8
    assert result.llm_provider == "groq"


def test_reasoning_agent_falls_back_to_ollama_on_groq_failure(mock_context):
    agent = ReasoningAgent(api_key="dummy")

    agent.structured_llm = MagicMock()
    agent.structured_llm.invoke.side_effect = RuntimeError("groq rate limited")

    ollama_snapshot = ReasoningSnapshot(
        recommendation="SELL",
        confidence=0.6,
        reasoning="Local model reasoning based on the same blackboard.",
        supporting_evidence=["Bearish order block"],
        conflicting_evidence=[],
        important_news=[],
        trade_quality_score=6,
    )
    agent.ollama_structured_llm = MagicMock()
    agent.ollama_structured_llm.invoke.return_value = ollama_snapshot

    result = agent.analyze(mock_context)

    agent.structured_llm.invoke.assert_called_once()
    agent.ollama_structured_llm.invoke.assert_called_once()
    assert result.recommendation == "SELL"
    assert result.llm_provider == "ollama"


def test_reasoning_agent_falls_back_to_wait_when_both_llms_fail(mock_context):
    agent = ReasoningAgent(api_key="dummy")

    agent.structured_llm = MagicMock()
    agent.structured_llm.invoke.side_effect = RuntimeError("groq down")

    agent.ollama_structured_llm = MagicMock()
    agent.ollama_structured_llm.invoke.side_effect = RuntimeError("ollama not running")

    result = agent.analyze(mock_context)

    assert result.recommendation == "WAIT"
    assert result.confidence == 0.0
    assert result.llm_provider == "fallback"
    assert "groq down" in result.reasoning
    assert "ollama not running" in result.reasoning
