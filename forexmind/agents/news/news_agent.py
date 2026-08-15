import logging
from datetime import datetime, timezone, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from forexmind.agents.news.schemas import NewsSnapshot, NewsArticle, EconomicEvent
from forexmind.agents.news.finnhub_client import FinnhubClient


class NewsAgent:
    """Agent responsible for fetching and evaluating Forex news and economic events."""

    def __init__(self, client: FinnhubClient | None = None):
        self.client = client or FinnhubClient()
        self.analyzer = SentimentIntensityAnalyzer()
        self.max_age_days = 7.0

    def _calculate_time_decay(self, event_time: datetime, as_of: datetime) -> float:
        """Calculates a linear time decay weight from 1.0 (now) to 0.0 (older than max_age)."""
        age_delta = as_of - event_time
        age_days = age_delta.total_seconds() / (24 * 3600)
        
        if age_days < 0:
            return 1.0  # Future events (like upcoming calendar events) stay highly relevant
            
        weight = 1.0 - (age_days / self.max_age_days)
        return max(0.0, weight)

    def _get_sentiment_label(self, score: float) -> str:
        if score >= 0.05:
            return "bullish"
        elif score <= -0.05:
            return "bearish"
        return "neutral"

    def get_snapshot(self, as_of: datetime | None = None) -> NewsSnapshot:
        """Fetches news and calendar data, calculates sentiment, and returns a snapshot."""
        if not as_of:
            as_of = datetime.now(timezone.utc)
            
        start_date = (as_of - timedelta(days=self.max_age_days)).strftime("%Y-%m-%d")
        end_date = (as_of + timedelta(days=2)).strftime("%Y-%m-%d") # Future events

        try:
            raw_news = self.client.get_forex_news()
            raw_events = self.client.get_economic_calendar(start_date=start_date, end_date=end_date)
        except Exception as e:
            logging.getLogger(__name__).warning("NewsAgent API failure, degrading gracefully: %s", e)
            raw_news = []
            raw_events = []

        articles = []
        events = []
        total_score = 0.0
        total_weight = 0.0

        for n in raw_news:
            dt = datetime.fromtimestamp(n.get("datetime", 0), tz=timezone.utc)
            weight = self._calculate_time_decay(dt, as_of)
            
            # Skip old news
            if weight == 0:
                continue

            headline = n.get("headline", "")
            summary = n.get("summary", "")
            text_to_analyze = f"{headline}. {summary}"
            
            scores = self.analyzer.polarity_scores(text_to_analyze)
            compound = scores.get("compound", 0.0)
            
            # Simple EUR/USD orientation (if it's good for USD, it's bearish for EUR/USD)
            # A robust implementation would check if 'USD' or 'EUR' is the subject.
            # We'll use a basic heuristic: if "US" or "Dollar" is mentioned and sentiment is positive, flip it.
            if "us dollar" in text_to_analyze.lower() or "fed" in text_to_analyze.lower():
                compound = -compound

            label = self._get_sentiment_label(compound)
            
            articles.append(NewsArticle(
                headline=headline,
                summary=summary,
                timestamp=dt.isoformat(),
                sentiment_score=compound,
                sentiment_label=label,
                time_decay_weight=weight
            ))
            
            total_score += (compound * weight)
            total_weight += weight

        for e in raw_events:
            try:
                dt_str = e.get("time", "")
                if " " in dt_str:
                    # e.g., '2026-08-08 13:30:00'
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                else:
                    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except ValueError:
                dt = as_of
                
            weight = self._calculate_time_decay(dt, as_of)
            if weight == 0:
                continue
                
            # Naive sentiment based on actual vs estimate
            actual = e.get("actual")
            estimate = e.get("estimate")
            event_compound = 0.0
            
            if actual is not None and estimate is not None:
                try:
                    act_val = float(actual)
                    est_val = float(estimate)
                    if act_val > est_val:
                        event_compound = -0.5 # Better US data = Bearish EUR/USD
                    elif act_val < est_val:
                        event_compound = 0.5 # Worse US data = Bullish EUR/USD
                except ValueError:
                    pass
            
            label = self._get_sentiment_label(event_compound)
            
            events.append(EconomicEvent(
                event_name=e.get("event", "Unknown"),
                impact=e.get("impact", "low"),
                expected=str(estimate) if estimate is not None else None,
                actual=str(actual) if actual is not None else None,
                timestamp=dt.isoformat(),
                sentiment_label=label,
                time_decay_weight=weight
            ))
            
            # Let's say high impact events have higher base weight
            impact_multiplier = 2.0 if e.get("impact") == "high" else 1.0
            total_score += (event_compound * weight * impact_multiplier)
            total_weight += (weight * impact_multiplier)

        overall_compound = (total_score / total_weight) if total_weight > 0 else 0.0
        overall_label = self._get_sentiment_label(overall_compound)

        return NewsSnapshot(
            as_of=as_of.isoformat(),
            overall_sentiment=overall_label,
            articles=articles,
            events=events
        )
