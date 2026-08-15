import os
import json
from datetime import datetime, timezone
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from forexmind.orchestration.market_context import MarketContext
from forexmind.agents.reasoning.schemas import ReasoningSnapshot

SYSTEM_PROMPT = """You are ForexMind, an autonomous multi-agent forex market analyst.
You have been provided with a highly detailed, mathematical 'Blackboard' containing the outputs of 11 distinct analytical agents.

Your task is to synthesize this data and issue a final trading recommendation.
You must output a strictly structured JSON object matching the requested schema.

CONFLICT RESOLUTION RULES:
1. SMC (Smart Money Concepts) and Risk Analysis are PRIMARY. If they conflict with Classical TA, favor SMC.
2. Elliott Wave and Wyckoff are ADVISORY. Use them for confidence, but do not override SMC or Risk bounds based on them.
3. News Sentiment is an OVERRIDE if it shows extreme bullish/bearish divergence from the technicals.
4. If Risk Analysis flags 'SL too wide' or 'R:R < 1', you MUST recommend WAIT. Do not force trades.
5. Historical Similarity is a CONFIDENCE MODIFIER. If similarity < 50%, lower your confidence. If similarity > 80% with a winning setup, raise it.
6. The Learning Agent (learning_metrics) provides a mathematically derived `confidence_modifier` based on historical win-rates of similar setups. You MUST add this modifier to your final confidence score to adjust for recent market regimes.

Do not hallucinate data. Only cite evidence found in the Blackboard context.
"""

class ReasoningAgent:
    """The central LLM agent that synthesizes all context into a final trade decision."""
    
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("GROQ_API_KEY", "mock_key")
        self.llm = ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=key,
            model="llama-3.1-70b-versatile",
            temperature=0.1
        )
        self.structured_llm = self.llm.with_structured_output(ReasoningSnapshot)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "Here is the compiled Blackboard (MarketContext) for {symbol}:\n\n{context_json}")
        ])
        
    def analyze(self, context: MarketContext) -> ReasoningSnapshot:
        # Convert Pydantic context to JSON string, excluding None/empty values to save tokens
        context_json = context.model_dump_json(exclude_none=True, exclude_defaults=True)
        
        # Format the prompt
        messages = self.prompt.format_messages(
            symbol=context.symbol,
            context_json=context_json
        )
        
        # Invoke LLM (in tests, this will be mocked)
        try:
            result: ReasoningSnapshot = self.structured_llm.invoke(messages)
            return result
        except Exception as e:
            logging.getLogger(__name__).error("ReasoningAgent LLM failure: %s", e)
            return ReasoningSnapshot(
                recommendation="WAIT",
                confidence=0.0,
                entry=None,
                stop_loss=None,
                take_profit=None,
                reasoning=f"System fallback due to LLM API error: {e}",
                supporting_evidence=[],
                conflicting_evidence=["LLM API Unavailable"],
                important_news=[],
                trade_quality_score=0
            )
