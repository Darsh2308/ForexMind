import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from forexmind.agents.chat.chat_agent import ChatAgent, _FALLBACK_REPLY

CONTEXT_JSON = '{"symbol": "EUR/USD", "reasoning_output": {"recommendation": "WAIT"}}'


def test_chat_agent_replies_via_groq():
    agent = ChatAgent(api_key="dummy")

    agent.llm = MagicMock()
    agent.llm.invoke.return_value = AIMessage(content="Risk Analysis found no valid setup, so WAIT.")

    reply, provider = agent.reply(CONTEXT_JSON, "Why WAIT?")

    agent.llm.invoke.assert_called_once()
    assert reply == "Risk Analysis found no valid setup, so WAIT."
    assert provider == "groq"


def test_chat_agent_falls_back_to_ollama_on_groq_failure():
    agent = ChatAgent(api_key="dummy")

    agent.llm = MagicMock()
    agent.llm.invoke.side_effect = RuntimeError("groq rate limited")

    agent.ollama_llm = MagicMock()
    agent.ollama_llm.invoke.return_value = AIMessage(content="Local model answer.")

    reply, provider = agent.reply(CONTEXT_JSON, "Why WAIT?")

    agent.llm.invoke.assert_called_once()
    agent.ollama_llm.invoke.assert_called_once()
    assert reply == "Local model answer."
    assert provider == "ollama"


def test_chat_agent_falls_back_to_plain_reply_when_both_llms_fail():
    agent = ChatAgent(api_key="dummy")

    agent.llm = MagicMock()
    agent.llm.invoke.side_effect = RuntimeError("groq down")

    agent.ollama_llm = MagicMock()
    agent.ollama_llm.invoke.side_effect = RuntimeError("ollama not running")

    reply, provider = agent.reply(CONTEXT_JSON, "Why WAIT?")

    assert reply == _FALLBACK_REPLY
    assert provider == "fallback"


def test_chat_agent_passes_history_as_prior_turns():
    agent = ChatAgent(api_key="dummy")
    agent.llm = MagicMock()
    agent.llm.invoke.return_value = AIMessage(content="Following up on that...")

    agent.reply(
        CONTEXT_JSON,
        "And the entry?",
        history=[("user", "Why WAIT?"), ("assistant", "No valid setup was found.")],
    )

    messages = agent.llm.invoke.call_args[0][0]
    # system + blackboard + 2 history turns + new message = 5
    assert len(messages) == 5
    assert messages[-1].content == "And the entry?"
