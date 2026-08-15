import sqlite3
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from forexmind.agents.technical_analysis.schemas import IndicatorSet
from forexmind.orchestration.timeframe_selector import select_timeframes


@pytest.fixture
def mock_conn():
    return MagicMock(spec=sqlite3.Connection)


@pytest.fixture
def mock_ta_agent():
    with patch("forexmind.orchestration.timeframe_selector.TechnicalAnalysisAgent") as mock:
        yield mock


@pytest.fixture
def mock_fetch_latest():
    with patch("forexmind.orchestration.timeframe_selector.fetch_latest_candle_at_or_before") as mock:
        yield mock


@pytest.fixture
def mock_active_sessions():
    with patch("forexmind.orchestration.timeframe_selector.active_sessions") as mock:
        yield mock


def test_select_timeframes_high_volatility(mock_conn, mock_ta_agent, mock_fetch_latest, mock_active_sessions):
    """Test that high volatility triggers Scalping/Fast Intraday timeframes."""
    mock_active_sessions.return_value = ["London"]  # Not overlapping with NY
    
    ta_instance = mock_ta_agent.return_value
    ta_instance.analyze_timeframe.return_value = IndicatorSet(atr_14=0.0070)
    
    mock_fetch_latest.return_value = {"close": 1.0000}  # Normalized ATR = 0.0070 (High)
    
    timeframes = select_timeframes(mock_conn, as_of="2026-08-08T10:00:00Z")
    assert timeframes == ["5min", "15min", "1h", "4h"]


def test_select_timeframes_high_activity_session(mock_conn, mock_ta_agent, mock_fetch_latest, mock_active_sessions):
    """Test that session overlap (London+NY) triggers Scalping/Fast Intraday timeframes."""
    mock_active_sessions.return_value = ["London", "New York"]
    
    ta_instance = mock_ta_agent.return_value
    ta_instance.analyze_timeframe.return_value = IndicatorSet(atr_14=0.0030)
    
    mock_fetch_latest.return_value = {"close": 1.0000}  # Normalized ATR = 0.0030 (Low)
    
    timeframes = select_timeframes(mock_conn, as_of="2026-08-08T14:00:00Z")
    assert timeframes == ["5min", "15min", "1h", "4h"]


def test_select_timeframes_low_activity_session(mock_conn, mock_ta_agent, mock_fetch_latest, mock_active_sessions):
    """Test that quiet Asian session with low volatility triggers Swing timeframes."""
    mock_active_sessions.return_value = ["Tokyo", "Sydney"]
    
    ta_instance = mock_ta_agent.return_value
    ta_instance.analyze_timeframe.return_value = IndicatorSet(atr_14=0.0020)
    
    mock_fetch_latest.return_value = {"close": 1.0000}  # Normalized ATR = 0.0020 (Low)
    
    timeframes = select_timeframes(mock_conn, as_of="2026-08-08T02:00:00Z")
    assert timeframes == ["1h", "4h", "1day"]


def test_select_timeframes_normal_activity(mock_conn, mock_ta_agent, mock_fetch_latest, mock_active_sessions):
    """Test that a single major session with normal volatility triggers Intraday timeframes."""
    mock_active_sessions.return_value = ["London"]
    
    ta_instance = mock_ta_agent.return_value
    ta_instance.analyze_timeframe.return_value = IndicatorSet(atr_14=0.0040)
    
    mock_fetch_latest.return_value = {"close": 1.0000}  # Normalized ATR = 0.0040 (Normal)
    
    timeframes = select_timeframes(mock_conn, as_of="2026-08-08T09:00:00Z")
    assert timeframes == ["15min", "1h", "4h"]


def test_select_timeframes_missing_data(mock_conn, mock_ta_agent, mock_fetch_latest, mock_active_sessions):
    """Test gracefully handling missing database records."""
    mock_active_sessions.return_value = ["London"]
    
    ta_instance = mock_ta_agent.return_value
    ta_instance.analyze_timeframe.return_value = IndicatorSet()  # Missing ATR
    
    mock_fetch_latest.return_value = None  # Missing Candle
    
    timeframes = select_timeframes(mock_conn, as_of="2026-08-08T09:00:00Z")
    assert timeframes == ["15min", "1h", "4h"]  # Defaults to intraday on normal session
