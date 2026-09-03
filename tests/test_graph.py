import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from forexmind.orchestration.graph import create_analysis_graph
from forexmind.orchestration.market_context import MarketContext


@pytest.fixture
def mock_conn():
    return MagicMock(spec=sqlite3.Connection)


from forexmind.agents.market_data.schemas import MarketDataSnapshot, SessionState
from forexmind.agents.technical_analysis.schemas import TechnicalAnalysisSnapshot
from forexmind.agents.price_action.schemas import PriceActionSnapshot
from forexmind.agents.candlestick.schemas import CandlestickSnapshot
from forexmind.agents.support_resistance.schemas import SupportResistanceSnapshot
from forexmind.agents.smc.schemas import SMCSnapshot
from forexmind.agents.elliott_wave.schemas import ElliottWaveSnapshot
from forexmind.agents.wyckoff.schemas import WyckoffSnapshot
from forexmind.agents.reasoning.schemas import ReasoningSnapshot

@pytest.fixture
def mock_agents():
    # Patch all the agent classes and timeframe_selector used in the graph
    patches = [
        patch("forexmind.orchestration.graph.select_timeframes", return_value=["15min", "1h"]),
        patch("forexmind.orchestration.graph.MarketDataAgent"),
        patch("forexmind.orchestration.graph.TechnicalAnalysisAgent"),
        patch("forexmind.orchestration.graph.PriceActionAgent"),
        patch("forexmind.orchestration.graph.CandlestickAgent"),
        patch("forexmind.orchestration.graph.SupportResistanceAgent"),
        patch("forexmind.orchestration.graph.SMCAgent"),
        patch("forexmind.orchestration.graph.ElliottWaveAgent"),
        patch("forexmind.orchestration.graph.WyckoffAgent"),
        patch("forexmind.orchestration.graph.ReasoningAgent"),
    ]
    
    mocks = [p.start() for p in patches]
    
    # Configure mock returns for all agents
    mocks[1].return_value.get_snapshot.return_value = MarketDataSnapshot(as_of="2026", is_live=False, sessions=SessionState(active_sessions=[], overlaps=[]))
    mocks[2].return_value.analyze.return_value = TechnicalAnalysisSnapshot(as_of="2026")
    mocks[3].return_value.analyze.return_value = PriceActionSnapshot(as_of="2026")
    mocks[4].return_value.analyze.return_value = CandlestickSnapshot(as_of="2026")
    mocks[5].return_value.analyze.return_value = SupportResistanceSnapshot(as_of="2026")
    mocks[6].return_value.analyze.return_value = SMCSnapshot(as_of="2026")
    mocks[7].return_value.analyze.return_value = ElliottWaveSnapshot(as_of="2026")
    mocks[8].return_value.analyze.return_value = WyckoffSnapshot(as_of="2026")
    mocks[9].return_value.analyze.return_value = ReasoningSnapshot(
        recommendation="WAIT", confidence=0.0, reasoning="test", 
        supporting_evidence=[], conflicting_evidence=[], important_news=[], trade_quality_score=5
    )
    
    yield
    
    for p in patches:
        p.stop()


def test_graph_execution(mock_conn, mock_agents):
    """Test that the graph compiles and executes end-to-end, returning a fully populated MarketContext."""
    graph = create_analysis_graph()
    
    initial_state = {
        "conn": mock_conn,
        "as_of": "2026-08-08T10:00:00Z",
        "symbol": "EUR/USD"
    }
    
    # Run the graph
    result = graph.invoke(initial_state)
    
    # Verify Context is built
    assert "market_context" in result
    ctx = result["market_context"]
    assert isinstance(ctx, MarketContext)
    
    # Verify that timeframes were passed
    assert ctx.timeframes == ["15min", "1h"]
    
    # Verify all agent outputs were merged properly
    assert ctx.market_data.as_of == "2026"
    assert ctx.technical_analysis.as_of == "2026"
    assert ctx.price_action.as_of == "2026"
    assert ctx.candlestick.as_of == "2026"
    assert getattr(ctx.support_resistance, "as_of", "2026") == "2026"
    assert ctx.smc.as_of == "2026"
    assert ctx.elliott_wave.as_of == "2026"
    assert ctx.wyckoff.as_of == "2026"
    
    # Verify conflicts were populated
    assert "conflicts" in result
    assert isinstance(result["conflicts"], list)
    assert ctx.conflicts == []


def test_graph_degrades_gracefully_on_agent_failure(mock_conn, mock_agents):
    """A non-critical agent crashing (e.g. SMC) must not crash the whole
    pipeline (Phase 17) - the run should still reach a final recommendation,
    and the failure should be recorded as a pipeline alert."""
    with patch("forexmind.orchestration.graph.SMCAgent") as mock_smc_cls, \
         patch("forexmind.orchestration.graph.send_alert") as mock_send_alert:
        mock_smc_cls.return_value.analyze.side_effect = RuntimeError("SMC detector blew up")

        graph = create_analysis_graph()
        result = graph.invoke({
            "conn": mock_conn,
            "as_of": "2026-08-08T10:00:00Z",
            "symbol": "EUR/USD",
        })

        ctx = result["market_context"]
        assert ctx.smc is None
        assert ctx.reasoning_output is not None
        assert ctx.reasoning_output.recommendation == "WAIT"

        mock_send_alert.assert_called_once()
        _, kwargs = mock_send_alert.call_args
        assert kwargs["source"] == "smc"
        assert kwargs["severity"] == "warning"
        assert "SMC detector blew up" in kwargs["message"]


def test_graph_reraises_on_critical_node_failure(mock_conn, mock_agents):
    """fetch_market_data has no meaningful degraded path - its failure must
    propagate rather than silently continuing with no data."""
    with patch("forexmind.orchestration.graph.select_timeframes", side_effect=RuntimeError("db unreachable")), \
         patch("forexmind.orchestration.graph.send_alert") as mock_send_alert:

        graph = create_analysis_graph()
        with pytest.raises(Exception, match="db unreachable"):
            graph.invoke({
                "conn": mock_conn,
                "as_of": "2026-08-08T10:00:00Z",
                "symbol": "EUR/USD",
            })

        mock_send_alert.assert_called_once()
        _, kwargs = mock_send_alert.call_args
        assert kwargs["source"] == "fetch_market_data"
        assert kwargs["severity"] == "critical"
