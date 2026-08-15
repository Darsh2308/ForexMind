from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from forexmind.agents.news.news_agent import NewsAgent
from forexmind.agents.news.finnhub_client import FinnhubClient
from forexmind.agents.news.schemas import NewsSnapshot


@pytest.fixture
def mock_finnhub_client():
    client = MagicMock(spec=FinnhubClient)
    # Provide synthetic forex news
    client.get_forex_news.return_value = [
        {
            "headline": "Federal Reserve announces great success and a remarkably strong US Dollar.",
            "summary": "This excellent hawkish move causes the US Dollar to rally strongly.",
            "datetime": int(datetime.now(timezone.utc).timestamp())
        },
        {
            "headline": "European Central Bank cuts rates.",
            "summary": "A dovish move by the ECB.",
            "datetime": int((datetime.now(timezone.utc) - timedelta(days=3)).timestamp())
        },
        {
            "headline": "Irrelevant old news.",
            "summary": "This should be ignored due to age.",
            "datetime": int((datetime.now(timezone.utc) - timedelta(days=10)).timestamp())
        }
    ]
    # Provide synthetic economic events
    client.get_economic_calendar.return_value = [
        {
            "event": "Nonfarm Payrolls",
            "impact": "high",
            "estimate": 200000,
            "actual": 300000,
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }
    ]
    return client


def test_news_agent_time_decay(mock_finnhub_client):
    agent = NewsAgent(client=mock_finnhub_client)
    now = datetime.now(timezone.utc)
    
    # Very recent event -> weight ~ 1.0
    weight_recent = agent._calculate_time_decay(now, now)
    assert weight_recent == 1.0
    
    # 3.5 days old event -> weight ~ 0.5
    half_time = now - timedelta(days=3.5)
    weight_half = agent._calculate_time_decay(half_time, now)
    assert 0.49 < weight_half < 0.51
    
    # 8 days old event -> weight 0.0 (beyond max_age_days)
    old_time = now - timedelta(days=8)
    weight_old = agent._calculate_time_decay(old_time, now)
    assert weight_old == 0.0


def test_news_agent_snapshot(mock_finnhub_client):
    agent = NewsAgent(client=mock_finnhub_client)
    
    snapshot = agent.get_snapshot()
    
    assert isinstance(snapshot, NewsSnapshot)
    
    # 3 news articles returned by mock, but 1 is older than 7 days
    assert len(snapshot.articles) == 2
    
    # The first article is hawkish Fed (USD bullish) -> expected to be mapped to bearish for EUR/USD
    article_1 = snapshot.articles[0]
    assert "Federal Reserve" in article_1.headline
    assert article_1.sentiment_score < 0 # Because US Dollar positive -> EUR/USD negative
    assert article_1.sentiment_label == "bearish"
    assert article_1.time_decay_weight > 0.9
    
    # The second article is ECB cuts (EUR bearish)
    article_2 = snapshot.articles[1]
    assert "European Central Bank" in article_2.headline
    # Simple vader might just see "cuts" as negative
    assert article_2.time_decay_weight < 1.0
    
    # 1 economic event returned by mock
    assert len(snapshot.events) == 1
    event_1 = snapshot.events[0]
    assert event_1.event_name == "Nonfarm Payrolls"
    assert event_1.actual == "300000"
    assert event_1.sentiment_label == "bearish" # Actual (300k) > Estimate (200k) -> Better USD -> Bearish EUR/USD
    
    # Overall sentiment should be bearish due to strong USD news
    assert snapshot.overall_sentiment == "bearish"
