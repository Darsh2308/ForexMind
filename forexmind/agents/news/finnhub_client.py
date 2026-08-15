import os
import requests
import time
from datetime import datetime, timedelta

class FinnhubClient:
    _news_cache = None
    _news_cache_time = 0.0
    _calendar_cache = {}

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY", "dummy")
        self.base_url = "https://finnhub.io/api/v1"
        self.cache_ttl = 900  # 15 minutes

    def get_forex_news(self) -> list[dict]:
        """Fetches recent forex news from Finnhub."""
        if self.api_key == "dummy" or self.api_key == "dummy_key_for_graph_v1":
            # Return synthetic data for testing
            return [
                {
                    "headline": "ECB unexpectedly raises interest rates by 50 basis points.",
                    "summary": "The European Central Bank surprised markets with a hawkish hike.",
                    "datetime": int((datetime.now() - timedelta(hours=2)).timestamp()),
                },
                {
                    "headline": "US Dollar Index plunges as inflation cools.",
                    "summary": "CPI data came in lower than expected.",
                    "datetime": int((datetime.now() - timedelta(days=2)).timestamp()),
                }
            ]
        
        
        now = time.time()
        if FinnhubClient._news_cache is not None and (now - FinnhubClient._news_cache_time) < self.cache_ttl:
            return FinnhubClient._news_cache

        url = f"{self.base_url}/news?category=forex&token={self.api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        FinnhubClient._news_cache = response.json()
        FinnhubClient._news_cache_time = now
        
        return FinnhubClient._news_cache

    def get_economic_calendar(self, start_date: str, end_date: str) -> list[dict]:
        """Fetches the economic calendar from Finnhub."""
        if self.api_key == "dummy" or self.api_key == "dummy_key_for_graph_v1":
            # Return synthetic data
            return [
                {
                    "event": "Nonfarm Payrolls",
                    "impact": "high",
                    "estimate": 200000,
                    "actual": 250000,
                    "time": f"{start_date} 13:30:00"
                }
            ]
            
        cache_key = f"{start_date}_{end_date}"
        now = time.time()
        cached = FinnhubClient._calendar_cache.get(cache_key)
        if cached and (now - cached["time"]) < self.cache_ttl:
            return cached["data"]
            
        url = f"{self.base_url}/calendar/economic?from={start_date}&to={end_date}&token={self.api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json().get("economicCalendar", [])
        
        FinnhubClient._calendar_cache[cache_key] = {"data": data, "time": now}
        return data
