from unittest.mock import patch

import pytest
import requests

from forexmind.agents.market_data.twelve_data_client import (
    TwelveDataClient,
    TwelveDataError,
)


def _mock_response(json_payload, status_ok=True):
    class _Resp:
        def raise_for_status(self):
            if not status_ok:
                raise requests.exceptions.HTTPError("401 Client Error: Unauthorized")

        def json(self):
            return json_payload

    return _Resp()


def test_requires_api_key(tmp_path):
    with pytest.raises(TwelveDataError):
        TwelveDataClient(api_key="", rate_limit_state_path=tmp_path / "rl.json")


def test_http_error_is_wrapped_as_twelve_data_error(tmp_path):
    """A raw requests exception (auth failure, rate limit, timeout, 5xx) must
    surface as TwelveDataError - that's the only exception type callers like
    MarketDataAgent's live-quote path are set up to catch and degrade on."""
    client = TwelveDataClient(
        api_key="bad-key", rate_limit_state_path=tmp_path / "rl.json"
    )
    with patch(
        "requests.get", return_value=_mock_response({}, status_ok=False)
    ):
        with pytest.raises(TwelveDataError):
            client.get_price()


def test_get_price_parses_response(tmp_path):
    client = TwelveDataClient(
        api_key="fake-key", rate_limit_state_path=tmp_path / "rl.json"
    )
    with patch("requests.get", return_value=_mock_response({"price": "1.0959"})):
        price = client.get_price()
    assert price == 1.0959


def test_get_time_series_parses_candles(tmp_path):
    client = TwelveDataClient(
        api_key="fake-key", rate_limit_state_path=tmp_path / "rl.json"
    )
    payload = {
        "values": [
            {
                "datetime": "2024-01-02",
                "open": "1.0950",
                "high": "1.0960",
                "low": "1.0944",
                "close": "1.0959",
                "volume": "0",
            }
        ]
    }
    with patch("requests.get", return_value=_mock_response(payload)):
        candles = client.get_time_series(interval="1day", outputsize=1)

    assert len(candles) == 1
    assert candles[0]["close"] == 1.0959
    assert candles[0]["timestamp"] == "2024-01-02"


def test_get_time_series_defaults_to_utc_timezone_param(tmp_path):
    client = TwelveDataClient(
        api_key="fake-key", rate_limit_state_path=tmp_path / "rl.json"
    )
    with patch("requests.get", return_value=_mock_response({"values": []})) as mock_get:
        client.get_time_series(interval="15min", outputsize=1)

    assert mock_get.call_args.kwargs["params"]["timezone"] == "UTC"


def test_get_quote_parses_response(tmp_path):
    client = TwelveDataClient(
        api_key="fake-key", rate_limit_state_path=tmp_path / "rl.json"
    )
    payload = {
        "datetime": "2026-07-26",
        "open": "1.13742",
        "high": "1.13782",
        "low": "1.13675",
        "close": "1.13684",
        "previous_close": "1.13742",
        "percent_change": "-0.053630145",
        "is_market_open": True,
    }
    with patch("requests.get", return_value=_mock_response(payload)):
        quote = client.get_quote()

    assert quote["close"] == 1.13684
    assert quote["is_market_open"] is True
    assert quote["percent_change"] == pytest.approx(-0.05363, abs=1e-4)


def test_get_quote_has_no_bid_ask_fields(tmp_path):
    """Documents the confirmed free-tier limitation: no spread is derivable
    from this endpoint. If Twelve Data ever adds bid/ask, this test should
    be updated alongside a real get_spread() implementation."""
    client = TwelveDataClient(
        api_key="fake-key", rate_limit_state_path=tmp_path / "rl.json"
    )
    payload = {
        "datetime": "2026-07-26",
        "open": "1.13742",
        "high": "1.13782",
        "low": "1.13675",
        "close": "1.13684",
        "is_market_open": True,
    }
    with patch("requests.get", return_value=_mock_response(payload)):
        quote = client.get_quote()

    assert "bid" not in quote
    assert "ask" not in quote


def test_api_error_response_raises(tmp_path):
    client = TwelveDataClient(
        api_key="fake-key", rate_limit_state_path=tmp_path / "rl.json"
    )
    error_payload = {"status": "error", "message": "invalid symbol"}
    with patch("requests.get", return_value=_mock_response(error_payload)):
        with pytest.raises(TwelveDataError, match="invalid symbol"):
            client.get_price()


def test_local_daily_budget_is_enforced(tmp_path):
    state_path = tmp_path / "rl.json"
    client = TwelveDataClient(
        api_key="fake-key", daily_request_limit=2, rate_limit_state_path=state_path
    )
    with patch("requests.get", return_value=_mock_response({"price": "1.0959"})):
        client.get_price()
        client.get_price()
        with pytest.raises(TwelveDataError, match="budget"):
            client.get_price()


def test_daily_budget_persists_across_client_instances(tmp_path):
    state_path = tmp_path / "rl.json"
    with patch("requests.get", return_value=_mock_response({"price": "1.0959"})):
        TwelveDataClient(
            api_key="fake-key", daily_request_limit=1, rate_limit_state_path=state_path
        ).get_price()

        second_client = TwelveDataClient(
            api_key="fake-key", daily_request_limit=1, rate_limit_state_path=state_path
        )
        with pytest.raises(TwelveDataError, match="budget"):
            second_client.get_price()
