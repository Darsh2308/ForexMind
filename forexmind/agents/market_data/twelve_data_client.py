"""Thin client around the Twelve Data REST API (free tier: 800 requests/day).

Only the endpoints Phase 1 (Market Data Agent) needs are wrapped: latest price
and time-series OHLC. A local, file-persisted counter guards the daily quota
so the app fails fast with a clear error instead of burning through the quota
and getting an opaque 429 from the API.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://api.twelvedata.com"
DEFAULT_SYMBOL = "EUR/USD"


class TwelveDataError(RuntimeError):
    """Raised for API error responses and local rate-limit exhaustion."""


class _DailyRateLimiter:
    """Persists a request count + date to a small JSON file so the budget
    survives process restarts."""

    def __init__(self, state_path: Path, daily_limit: int):
        self._state_path = state_path
        self._daily_limit = daily_limit

    def _read_state(self) -> dict[str, Any]:
        if not self._state_path.exists():
            return {"date": None, "count": 0}
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"date": None, "count": 0}

    def _write_state(self, state: dict[str, Any]) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(state), encoding="utf-8")

    def check_and_increment(self) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        state = self._read_state()
        if state.get("date") != today:
            state = {"date": today, "count": 0}
        if state["count"] >= self._daily_limit:
            raise TwelveDataError(
                f"Local daily request budget ({self._daily_limit}) exhausted for {today}."
            )
        state["count"] += 1
        self._write_state(state)


class TwelveDataClient:
    _quote_cache = {}
    _quote_cache_ttl = 60  # 1 minute

    def __init__(
        self,
        api_key: str,
        daily_request_limit: int = 800,
        rate_limit_state_path: Path | None = None,
        timeout_seconds: float = 10.0,
    ):
        if not api_key:
            raise TwelveDataError("TwelveDataClient requires a non-empty api_key.")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        state_path = rate_limit_state_path or (
            Path(__file__).resolve().parent.parent.parent.parent
            / "var"
            / "twelve_data_rate_limit.json"
        )
        self._rate_limiter = _DailyRateLimiter(state_path, daily_request_limit)

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        self._rate_limiter.check_and_increment()
        try:
            response = requests.get(
                f"{BASE_URL}/{endpoint}",
                params={**params, "apikey": self._api_key},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as e:
            # Callers (e.g. MarketDataAgent's live-quote path) only handle
            # TwelveDataError - normalize every transport/HTTP-status failure
            # (auth, rate limit, timeout, DNS, 5xx) to that one type so a
            # transient API failure degrades gracefully instead of leaking an
            # unhandled requests exception up through the whole pipeline.
            raise TwelveDataError(f"Twelve Data request to {endpoint!r} failed: {e}") from e
        if isinstance(payload, dict) and payload.get("status") == "error":
            raise TwelveDataError(payload.get("message", "Unknown Twelve Data API error"))
        return payload

    def get_price(self, symbol: str = DEFAULT_SYMBOL) -> float:
        payload = self._get("price", {"symbol": symbol})
        return float(payload["price"])

    def get_time_series(
        self,
        symbol: str = DEFAULT_SYMBOL,
        interval: str = "1day",
        outputsize: int = 1,
        timezone_: str = "UTC",
    ) -> list[dict[str, Any]]:
        """Twelve Data returns values newest-first; passed through unmodified
        since storage reads always re-sort by timestamp.

        `timezone_` is pinned to UTC by default so stored timestamps are
        directly, lexicographically comparable with `datetime.now(timezone.utc)`
        without a timezone-conversion step at query time.
        """
        payload = self._get(
            "time_series",
            {
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "timezone": timezone_,
            },
        )
        values = payload.get("values", [])
        candles = []
        for row in values:
            candles.append(
                {
                    "timestamp": row["datetime"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]) if row.get("volume") else None,
                }
            )
        return candles

    def get_quote(self, symbol: str = DEFAULT_SYMBOL) -> dict[str, Any]:
        """Latest OHLC + market-open status for `symbol`.

        Note: Twelve Data's free-tier quote response carries no bid/ask
        fields (verified against the live API) - spread is not obtainable
        from this provider without a paid plan, so callers should not expect
        one from this method.
        """
        import time
        now = time.time()
        cached = TwelveDataClient._quote_cache.get(symbol)
        if cached and (now - cached["time"]) < TwelveDataClient._quote_cache_ttl:
            return cached["data"]
            
        payload = self._get("quote", {"symbol": symbol})
        
        result = {
            "datetime": payload.get("datetime"),
            "open": float(payload["open"]),
            "high": float(payload["high"]),
            "low": float(payload["low"]),
            "close": float(payload["close"]),
            "previous_close": (
                float(payload["previous_close"]) if payload.get("previous_close") else None
            ),
            "percent_change": (
                float(payload["percent_change"]) if payload.get("percent_change") else None
            ),
            "is_market_open": bool(payload.get("is_market_open", False)),
        }
        
        TwelveDataClient._quote_cache[symbol] = {"data": result, "time": now}
        return result
