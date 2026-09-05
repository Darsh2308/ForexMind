import os
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

logger = logging.getLogger(__name__)

_WAIT_FALLBACK_KWARGS = dict(
    recommendation="WAIT",
    confidence=0.0,
    entry=None,
    stop_loss=None,
    take_profit=None,
    supporting_evidence=[],
    conflicting_evidence=["LLM API Unavailable"],
    important_news=[],
    trade_quality_score=1,
)


class ReasoningAgent:
    """The central LLM agent that synthesizes all context into a final trade decision.

    Groq (free tier) is the primary backend. If Groq is unreachable or
    rate-limited, a local Ollama server (same model family) is tried as an
    offline fallback per Phase 12. If both are unavailable, `analyze` returns
    a hard-coded WAIT recommendation rather than raising - the Reasoning
    Agent must never crash the pipeline.
    """

    def __init__(
        self,
        api_key: str | None = None,
        ollama_base_url: str | None = None,
        ollama_model: str | None = None,
    ):
        # os.getenv(VAR, default) only falls back when VAR is entirely unset -
        # a blank .env entry (VAR=) still counts as "set" to an empty string,
        # which ChatOpenAI/the OpenAI SDK treats as no credentials at all
        # instead of falling through. `or` treats blank the same as unset.
        groq_key = api_key or os.getenv("GROQ_API_KEY") or "mock_key"
        groq_model = os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile"
        self.llm = ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key,
            model=groq_model,
            temperature=0.1
        )
        self.structured_llm = self.llm.with_structured_output(ReasoningSnapshot)

        # Local Ollama fallback. Ollama exposes an OpenAI-compatible endpoint
        # that ignores the api_key value, but ChatOpenAI requires a non-empty
        # string to be passed.
        self.ollama_base_url = (
            ollama_base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"
        )
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL") or "llama3.3"
        self.ollama_llm = ChatOpenAI(
            base_url=self.ollama_base_url,
            api_key="ollama",
            model=self.ollama_model,
            temperature=0.1,
        )
        self.ollama_structured_llm = self.ollama_llm.with_structured_output(ReasoningSnapshot)

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

        groq_error_msg: str | None = None
        try:
            result: ReasoningSnapshot = self.structured_llm.invoke(messages)
            result.llm_provider = "groq"
            return result
        except Exception as e:
            groq_error_msg = str(e)
            logger.warning("ReasoningAgent Groq failure, falling back to local Ollama: %s", groq_error_msg)

        try:
            result = self.ollama_structured_llm.invoke(messages)
            result.llm_provider = "ollama"
            return result
        except Exception as e:
            ollama_error_msg = str(e)
            logger.error("ReasoningAgent Ollama fallback also failed: %s", ollama_error_msg)
            fallback = ReasoningSnapshot(
                reasoning=(
                    f"System fallback to WAIT: Groq API error ({groq_error_msg}) "
                    f"and local Ollama fallback also failed ({ollama_error_msg})."
                ),
                **_WAIT_FALLBACK_KWARGS,
            )
            fallback.llm_provider = "fallback"
            return fallback
