import os
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage

SYSTEM_PROMPT = """You are ForexMind, the same analyst that produced the trading
recommendation described in the Blackboard (MarketContext) below. A user is asking
you follow-up questions about THIS specific call - why it was made, what a specific
agent's finding means, whether a level or pattern matters.

Answer only from the evidence in the Blackboard you were given. Do not invent price
levels, indicators, or news that aren't present in it. If the Blackboard doesn't
contain something the user asks about, say so plainly instead of guessing.

Keep answers conversational and concise - a few sentences, not a report. This is a
chat, not another structured recommendation.
"""

logger = logging.getLogger(__name__)

_FALLBACK_REPLY = (
    "I can't reach either the primary or fallback language model right now, so I "
    "can't answer that this moment. The recommendation's own reasoning and evidence "
    "are still available above - please try again shortly."
)


class ChatAgent:
    """Grounded follow-up chat about one specific recommendation's stored
    MarketContext. Same Groq-primary/Ollama-fallback pattern as ReasoningAgent
    (forexmind/agents/reasoning/reasoning_agent.py), but returns plain text -
    there is no structured output schema for a conversational answer.
    """

    def __init__(
        self,
        api_key: str | None = None,
        ollama_base_url: str | None = None,
        ollama_model: str | None = None,
    ):
        groq_key = api_key or os.getenv("GROQ_API_KEY") or "mock_key"
        groq_model = os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile"
        self.llm = ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key,
            model=groq_model,
            temperature=0.3,
        )

        self.ollama_base_url = (
            ollama_base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"
        )
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL") or "llama3.3"
        self.ollama_llm = ChatOpenAI(
            base_url=self.ollama_base_url,
            api_key="ollama",
            model=self.ollama_model,
            temperature=0.3,
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "Here is the compiled Blackboard (MarketContext) for this recommendation:\n\n{context_json}"),
            MessagesPlaceholder("history"),
            ("user", "{message}"),
        ])

    def reply(
        self,
        context_json: str,
        message: str,
        history: list[tuple[str, str]] | None = None,
    ) -> tuple[str, str]:
        """Returns (reply_text, provider) where provider is 'groq', 'ollama', or
        'fallback' - mirrors ReasoningSnapshot.llm_provider so the frontend can
        show the same trust signal it already shows for the main recommendation."""
        history_messages = [
            HumanMessage(content=content) if role == "user" else AIMessage(content=content)
            for role, content in (history or [])
        ]
        messages = self.prompt.format_messages(
            context_json=context_json,
            history=history_messages,
            message=message,
        )

        groq_error_msg: str | None = None
        try:
            result = self.llm.invoke(messages)
            return str(result.content), "groq"
        except Exception as e:
            groq_error_msg = str(e)
            logger.warning("ChatAgent Groq failure, falling back to local Ollama: %s", groq_error_msg)

        try:
            result = self.ollama_llm.invoke(messages)
            return str(result.content), "ollama"
        except Exception as e:
            logger.error("ChatAgent Ollama fallback also failed: %s", e)
            return _FALLBACK_REPLY, "fallback"
