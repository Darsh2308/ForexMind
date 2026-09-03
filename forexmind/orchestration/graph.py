from typing import TypedDict, Any
from datetime import datetime, timezone
import sqlite3

from langgraph.graph import StateGraph, START, END

from forexmind.orchestration.market_context import MarketContext
from forexmind.orchestration.timeframe_selector import select_timeframes
from forexmind.orchestration.cross_validation import cross_validate

from forexmind.agents.market_data.market_data_agent import MarketDataAgent
from forexmind.agents.technical_analysis.technical_analysis_agent import TechnicalAnalysisAgent
from forexmind.agents.price_action.price_action_agent import PriceActionAgent
from forexmind.agents.candlestick.candlestick_agent import CandlestickAgent
from forexmind.agents.support_resistance.support_resistance_agent import SupportResistanceAgent
from forexmind.agents.smc.smc_agent import SMCAgent
from forexmind.agents.elliott_wave.elliott_wave_agent import ElliottWaveAgent
from forexmind.agents.wyckoff.wyckoff_agent import WyckoffAgent
from forexmind.storage.db import (
    fetch_latest_candle_at_or_before,
    insert_recommendation,
    insert_agent_snapshot
)
from forexmind.agents.market_data.twelve_data_client import TwelveDataClient
from forexmind.agents.news.news_agent import NewsAgent
from forexmind.agents.historical.historical_similarity_agent import HistoricalSimilarityAgent
from forexmind.agents.risk_analysis.risk_analysis_agent import RiskAnalysisAgent
from forexmind.agents.learning.learning_agent import LearningAgent
from forexmind.agents.reasoning.reasoning_agent import ReasoningAgent
from forexmind.monitoring.alerts import send_alert


class GraphState(TypedDict, total=False):
    """The state dictionary that LangGraph passes between nodes."""
    conn: sqlite3.Connection
    as_of: str
    symbol: str
    timeframes: list[str]
    market_data: Any
    technical_analysis: Any
    price_action: Any
    candlestick: Any
    support_resistance: Any
    smc: Any
    elliott_wave: Any
    wyckoff: Any
    news: Any
    market_context: Any
    conflicts: list[str]
    context: MarketContext


def fetch_market_data(state: GraphState) -> GraphState:
    conn = state["conn"]
    as_of = state.get("as_of")
    
    # Run timeframe selector
    timeframes = select_timeframes(conn, as_of=as_of)
    
    # Run Market Data Agent
    client = TwelveDataClient(api_key="dummy_key_for_graph_v1")
    md_agent = MarketDataAgent(client, conn)
    md_snapshot = md_agent.get_snapshot(
        datetime.fromisoformat(as_of.replace("Z", "+00:00")) if as_of else None
    )
    
    return {"timeframes": timeframes, "market_data": md_snapshot}


def run_technical_analysis(state: GraphState) -> GraphState:
    agent = TechnicalAnalysisAgent(state["conn"])
    return {"technical_analysis": agent.analyze(state["timeframes"], as_of=state.get("as_of"))}


def run_price_action(state: GraphState) -> GraphState:
    agent = PriceActionAgent(state["conn"])
    return {"price_action": agent.analyze(state["timeframes"], as_of=state.get("as_of"))}


def run_candlestick(state: GraphState) -> GraphState:
    agent = CandlestickAgent(state["conn"])
    return {"candlestick": agent.analyze(state["timeframes"], as_of=state.get("as_of"))}


def run_support_resistance(state: GraphState) -> GraphState:
    agent = SupportResistanceAgent(state["conn"])
    return {"support_resistance": agent.analyze(state["timeframes"], as_of=state.get("as_of"))}


def run_smc(state: GraphState) -> GraphState:
    agent = SMCAgent(state["conn"])
    return {"smc": agent.analyze(state["timeframes"], as_of=state.get("as_of"))}


def run_elliott_wave(state: GraphState) -> GraphState:
    agent = ElliottWaveAgent(state["conn"])
    return {"elliott_wave": agent.analyze(state["timeframes"], as_of=state.get("as_of"))}


def run_wyckoff(state: GraphState) -> GraphState:
    agent = WyckoffAgent(state["conn"])
    return {"wyckoff": agent.analyze(state["timeframes"], as_of=state.get("as_of"))}

def run_news(state: GraphState) -> GraphState:
    agent = NewsAgent()
    as_of_str = state.get("as_of")
    dt = datetime.fromisoformat(as_of_str.replace("Z", "+00:00")) if as_of_str else None
    return {"news": agent.get_snapshot(dt)}


def run_cross_validate(state: GraphState) -> GraphState:
    """Consolidates all parallel snapshots into MarketContext and runs cross-validation."""
    context = MarketContext(
        generated_at=datetime.now(timezone.utc),
        symbol=state.get("symbol", "EUR/USD"),
        timeframes=state.get("timeframes", []),
        market_data=state.get("market_data"),
        technical_analysis=state.get("technical_analysis"),
        price_action=state.get("price_action"),
        candlestick=state.get("candlestick"),
        support_resistance=state.get("support_resistance"),
        smc=state.get("smc"),
        elliott_wave=state.get("elliott_wave"),
        wyckoff=state.get("wyckoff"),
        news=state.get("news"),
    )
    
    conflicts = cross_validate(context)
    context.conflicts = conflicts
    return {"market_context": context, "conflicts": conflicts}

def run_historical_similarity(state: GraphState) -> GraphState:
    """Runs sequentially after cross_validate to compare the compiled MarketContext to history."""
    agent = HistoricalSimilarityAgent(state["conn"])
    snapshot = agent.analyze(state["market_context"])
    
    # Update the market context with the historical similarity
    context = state["market_context"]
    context.historical_similarity = snapshot
    
    return {"market_context": context, "conflicts": context.conflicts}

def run_risk_analysis(state: GraphState) -> GraphState:
    """Runs sequentially after historical_similarity to analyze risk."""
    agent = RiskAnalysisAgent()
    snapshot = agent.analyze(state["market_context"])
    
    # Update the market context with the risk analysis
    context = state["market_context"]
    context.risk_analysis = snapshot
    
    return {"market_context": context, "conflicts": context.conflicts}

def run_learning_agent(state: GraphState) -> GraphState:
    agent = LearningAgent(conn=state["conn"])
    snapshot = agent.analyze(state["market_context"])
    
    context = state["market_context"]
    context.learning_metrics = snapshot
    
    return {"market_context": context, "conflicts": context.conflicts}

def run_reasoning_agent(state: GraphState) -> GraphState:
    """Runs sequentially at the very end to issue a final recommendation."""
    agent = ReasoningAgent()
    snapshot = agent.analyze(state["market_context"])
    
    # Update the market context with the final reasoning output
    context = state["market_context"]
    context.reasoning_output = snapshot
    
    return {"market_context": context, "conflicts": context.conflicts}


def run_save_recommendation(state: GraphState) -> GraphState:
    """Saves valid BUY/SELL recommendations and their context to the database."""
    conn = state["conn"]
    context = state["market_context"]
    
    if context.reasoning_output and context.reasoning_output.recommendation in ("BUY", "SELL"):
        rec = context.reasoning_output
        rec_id = insert_recommendation(
            conn=conn,
            created_at=context.generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            recommendation=rec.recommendation,
            confidence=rec.confidence,
            entry=rec.entry,
            stop_loss=rec.stop_loss,
            take_profit=rec.take_profit,
            reasoning=rec.reasoning,
            status="PENDING"
        )
        insert_agent_snapshot(
            conn=conn,
            recommendation_id=rec_id,
            agent_name="market_context",
            payload=context.model_dump_json(exclude_none=True, exclude_defaults=True),
            created_at=context.generated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        
    return {"market_context": context, "conflicts": context.conflicts}

def _guarded(source: str, fn, critical: bool = False):
    """Wraps a graph node so a single agent's failure is logged/alerted and
    degrades gracefully (the node contributes nothing this run) instead of
    crashing the whole pipeline - Phase 17's "skip News Agent rather than
    crash the pipeline" requirement, generalized to every non-essential node.

    `critical` nodes (market data fetch, cross-validation) have no meaningful
    degraded path - there is nothing for downstream nodes to consume - so
    their failure is still alerted but then re-raised.
    """

    def wrapped(state: GraphState) -> GraphState:
        try:
            return fn(state)
        except Exception as e:
            send_alert(
                source=source,
                message=str(e),
                severity="critical" if critical else "warning",
                conn=state.get("conn"),
            )
            if critical:
                raise
            return {}

    return wrapped


def create_analysis_graph():
    """Builds and compiles the LangGraph state machine for multi-agent execution."""
    builder = StateGraph(GraphState)

    builder.add_node("fetch_market_data", _guarded("fetch_market_data", fetch_market_data, critical=True))
    builder.add_node("technical_analysis", _guarded("technical_analysis", run_technical_analysis))
    builder.add_node("price_action", _guarded("price_action", run_price_action))
    builder.add_node("candlestick", _guarded("candlestick", run_candlestick))
    builder.add_node("support_resistance", _guarded("support_resistance", run_support_resistance))
    builder.add_node("smc", _guarded("smc", run_smc))
    builder.add_node("elliott_wave", _guarded("elliott_wave", run_elliott_wave))
    builder.add_node("wyckoff", _guarded("wyckoff", run_wyckoff))
    builder.add_node("news", _guarded("news", run_news))
    builder.add_node("cross_validate", _guarded("cross_validate", run_cross_validate, critical=True))
    builder.add_node("historical_similarity", _guarded("historical_similarity", run_historical_similarity))
    builder.add_node("risk_analysis", _guarded("risk_analysis", run_risk_analysis))
    builder.add_node("learning", _guarded("learning", run_learning_agent))
    builder.add_node("reasoning", _guarded("reasoning", run_reasoning_agent))
    builder.add_node("save_recommendation", _guarded("save_recommendation", run_save_recommendation))
    
    builder.add_edge(START, "fetch_market_data")
    
    # Fan out from Market Data to all Analysis Agents
    builder.add_edge("fetch_market_data", "technical_analysis")
    builder.add_edge("fetch_market_data", "price_action")
    builder.add_edge("fetch_market_data", "candlestick")
    builder.add_edge("fetch_market_data", "support_resistance")
    builder.add_edge("fetch_market_data", "smc")
    builder.add_edge("fetch_market_data", "elliott_wave")
    builder.add_edge("fetch_market_data", "wyckoff")
    builder.add_edge("fetch_market_data", "news")
    
    # Fan in to Cross Validation
    builder.add_edge("technical_analysis", "cross_validate")
    builder.add_edge("price_action", "cross_validate")
    builder.add_edge("candlestick", "cross_validate")
    builder.add_edge("support_resistance", "cross_validate")
    builder.add_edge("smc", "cross_validate")
    builder.add_edge("elliott_wave", "cross_validate")
    builder.add_edge("wyckoff", "cross_validate")
    builder.add_edge("news", "cross_validate")
    
    # Sequential processing after parallel agents
    builder.add_edge("cross_validate", "historical_similarity")
    builder.add_edge("historical_similarity", "risk_analysis")
    builder.add_edge("risk_analysis", "learning")
    builder.add_edge("learning", "reasoning")
    builder.add_edge("reasoning", "save_recommendation")
    builder.add_edge("save_recommendation", END)
    
    return builder.compile()
