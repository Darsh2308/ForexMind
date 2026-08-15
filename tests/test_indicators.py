"""Unit tests for the pure indicator computation functions.

Reference values were independently computed from the golden fixture
(eurusd_sample.csv, 64 daily EUR/USD candles, Jan 2–Mar 29 2024)
using pandas_ta directly — see scratch/compute_reference_values.py.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest

from forexmind.agents.technical_analysis.indicators import (
    classify_rsi_zone,
    classify_stoch_zone,
    classify_trend,
    compute_atr,
    compute_bollinger_bands,
    compute_ema,
    compute_indicators,
    compute_macd,
    compute_rsi,
    compute_sma,
    compute_stochastic,
    detect_macd_cross,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Floating-point tolerance for indicator comparisons.
# pandas_ta uses IEEE 754 doubles internally — 1e-4 is generous enough to
# absorb any platform-level float-rounding while still catching real bugs.
TOLERANCE = 1e-4


@pytest.fixture
def golden_df() -> pd.DataFrame:
    """Load the golden fixture CSV into a pandas DataFrame (oldest first)."""
    rows = []
    with (FIXTURES_DIR / "eurusd_sample.csv").open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "timestamp": row["timestamp"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                }
            )
    return pd.DataFrame(rows)


# ── Hand-verified reference values ─────────────────────────────────────────
# Computed independently via scratch/compute_reference_values.py

REF_EMA_20 = 1.109702
REF_EMA_50 = 1.105636
REF_SMA_20 = 1.111356
REF_SMA_50 = 1.106026
REF_RSI_14 = 52.022464
REF_MACD_LINE = 0.000984
REF_MACD_SIGNAL = 0.001638
REF_MACD_HIST = -0.000654
REF_STOCH_K = 33.716769
REF_STOCH_D = 33.682686
REF_ATR_14 = 0.003413
REF_BB_UPPER = 1.117143
REF_BB_MIDDLE = 1.111356
REF_BB_LOWER = 1.105570
REF_BB_BANDWIDTH = 1.041362
REF_BB_PERCENT_B = 0.394023


# ── Trend indicator tests ─────────────────────────────────────────────────

class TestEMA:
    def test_ema_20_matches_reference(self, golden_df):
        result = compute_ema(golden_df["close"], 20)
        assert result is not None
        assert result == pytest.approx(REF_EMA_20, abs=TOLERANCE)

    def test_ema_50_matches_reference(self, golden_df):
        result = compute_ema(golden_df["close"], 50)
        assert result is not None
        assert result == pytest.approx(REF_EMA_50, abs=TOLERANCE)

    def test_ema_200_returns_none_with_insufficient_data(self, golden_df):
        """64 candles is not enough for a 200-period EMA."""
        result = compute_ema(golden_df["close"], 200)
        assert result is None

    def test_ema_returns_none_for_empty_series(self):
        result = compute_ema(pd.Series(dtype=float), 20)
        assert result is None


class TestSMA:
    def test_sma_20_matches_reference(self, golden_df):
        result = compute_sma(golden_df["close"], 20)
        assert result is not None
        assert result == pytest.approx(REF_SMA_20, abs=TOLERANCE)

    def test_sma_50_matches_reference(self, golden_df):
        result = compute_sma(golden_df["close"], 50)
        assert result is not None
        assert result == pytest.approx(REF_SMA_50, abs=TOLERANCE)

    def test_sma_200_returns_none_with_insufficient_data(self, golden_df):
        result = compute_sma(golden_df["close"], 200)
        assert result is None


# ── Momentum indicator tests ──────────────────────────────────────────────

class TestRSI:
    def test_rsi_14_matches_reference(self, golden_df):
        result = compute_rsi(golden_df["close"])
        assert result is not None
        assert result == pytest.approx(REF_RSI_14, abs=TOLERANCE)

    def test_rsi_returns_none_with_too_few_bars(self):
        result = compute_rsi(pd.Series([1.1] * 10))
        assert result is None


class TestMACD:
    def test_macd_matches_reference(self, golden_df):
        line, signal, hist = compute_macd(golden_df["close"])
        assert line is not None
        assert line == pytest.approx(REF_MACD_LINE, abs=TOLERANCE)
        assert signal is not None
        assert signal == pytest.approx(REF_MACD_SIGNAL, abs=TOLERANCE)
        assert hist is not None
        assert hist == pytest.approx(REF_MACD_HIST, abs=TOLERANCE)

    def test_macd_returns_nones_with_too_few_bars(self):
        line, signal, hist = compute_macd(pd.Series([1.1] * 20))
        assert line is None
        assert signal is None
        assert hist is None


class TestMACDCross:
    def test_no_cross_in_golden_fixture(self, golden_df):
        """The last 3 bars of the golden fixture have MACD consistently
        below signal — no cross."""
        result = detect_macd_cross(golden_df["close"])
        assert result == "none"

    def test_returns_none_with_insufficient_data(self):
        result = detect_macd_cross(pd.Series([1.1] * 20))
        assert result == "none"


class TestStochastic:
    def test_stochastic_matches_reference(self, golden_df):
        k, d = compute_stochastic(
            golden_df["high"], golden_df["low"], golden_df["close"]
        )
        assert k is not None
        assert k == pytest.approx(REF_STOCH_K, abs=TOLERANCE)
        assert d is not None
        assert d == pytest.approx(REF_STOCH_D, abs=TOLERANCE)

    def test_stochastic_returns_nones_with_too_few_bars(self):
        s = pd.Series([1.1] * 10)
        k, d = compute_stochastic(s, s, s)
        assert k is None
        assert d is None


# ── Volatility indicator tests ────────────────────────────────────────────

class TestATR:
    def test_atr_14_matches_reference(self, golden_df):
        result = compute_atr(golden_df["high"], golden_df["low"], golden_df["close"])
        assert result is not None
        assert result == pytest.approx(REF_ATR_14, abs=TOLERANCE)

    def test_atr_returns_none_with_too_few_bars(self):
        s = pd.Series([1.1] * 10)
        result = compute_atr(s, s, s)
        assert result is None


class TestBollingerBands:
    def test_bb_matches_reference(self, golden_df):
        upper, middle, lower, bw, pctb = compute_bollinger_bands(golden_df["close"])
        assert upper == pytest.approx(REF_BB_UPPER, abs=TOLERANCE)
        assert middle == pytest.approx(REF_BB_MIDDLE, abs=TOLERANCE)
        assert lower == pytest.approx(REF_BB_LOWER, abs=TOLERANCE)
        assert bw == pytest.approx(REF_BB_BANDWIDTH, abs=TOLERANCE)
        assert pctb == pytest.approx(REF_BB_PERCENT_B, abs=TOLERANCE)

    def test_bb_returns_nones_with_too_few_bars(self):
        result = compute_bollinger_bands(pd.Series([1.1] * 15))
        assert result == (None, None, None, None, None)


# ── Classification tests ─────────────────────────────────────────────────

class TestTrendClassification:
    def test_bullish_when_ema20_above_ema50(self):
        assert classify_trend(1.11, 1.10, None) == "bullish"

    def test_bearish_when_ema20_below_ema50(self):
        assert classify_trend(1.09, 1.10, None) == "bearish"

    def test_full_bullish_alignment(self):
        assert classify_trend(1.12, 1.11, 1.10) == "bullish"

    def test_full_bearish_alignment(self):
        assert classify_trend(1.08, 1.09, 1.10) == "bearish"

    def test_mixed_alignment_is_neutral(self):
        # EMA20 > EMA50 but EMA50 < EMA200
        assert classify_trend(1.11, 1.09, 1.10) == "neutral"

    def test_neutral_when_data_missing(self):
        assert classify_trend(None, None, None) == "neutral"
        assert classify_trend(1.1, None, None) == "neutral"

    def test_golden_fixture_is_bullish(self, golden_df):
        """EMA-20 > EMA-50 in the golden fixture → bullish."""
        indicators = compute_indicators(golden_df)
        assert indicators.trend == "bullish"


class TestRSIZone:
    def test_overbought(self):
        assert classify_rsi_zone(75.0) == "overbought"

    def test_oversold(self):
        assert classify_rsi_zone(25.0) == "oversold"

    def test_neutral(self):
        assert classify_rsi_zone(50.0) == "neutral"

    def test_boundary_overbought(self):
        assert classify_rsi_zone(70.0) == "neutral"  # > 70, not >=
        assert classify_rsi_zone(70.1) == "overbought"

    def test_none_is_neutral(self):
        assert classify_rsi_zone(None) == "neutral"


class TestStochZone:
    def test_overbought(self):
        assert classify_stoch_zone(85.0) == "overbought"

    def test_oversold(self):
        assert classify_stoch_zone(15.0) == "oversold"

    def test_neutral(self):
        assert classify_stoch_zone(50.0) == "neutral"

    def test_none_is_neutral(self):
        assert classify_stoch_zone(None) == "neutral"


# ── Full compute_indicators integration ───────────────────────────────────

class TestComputeIndicators:
    def test_full_golden_fixture(self, golden_df):
        """End-to-end: compute all indicators from the golden fixture and
        verify the overall shape and key values."""
        result = compute_indicators(golden_df)

        # Trend
        assert result.ema_20 == pytest.approx(REF_EMA_20, abs=TOLERANCE)
        assert result.ema_50 == pytest.approx(REF_EMA_50, abs=TOLERANCE)
        assert result.ema_200 is None  # Not enough data
        assert result.sma_20 == pytest.approx(REF_SMA_20, abs=TOLERANCE)
        assert result.ema_20_above_ema_50 is True
        assert result.ema_50_above_ema_200 is None  # No EMA-200
        assert result.trend == "bullish"

        # Momentum
        assert result.rsi_14 == pytest.approx(REF_RSI_14, abs=TOLERANCE)
        assert result.rsi_zone == "neutral"
        assert result.macd_line == pytest.approx(REF_MACD_LINE, abs=TOLERANCE)
        assert result.stoch_k == pytest.approx(REF_STOCH_K, abs=TOLERANCE)
        assert result.stoch_zone == "neutral"

        # Volatility
        assert result.atr_14 == pytest.approx(REF_ATR_14, abs=TOLERANCE)
        assert result.bb_upper == pytest.approx(REF_BB_UPPER, abs=TOLERANCE)

    def test_empty_dataframe_returns_defaults(self):
        """Empty input → all Nones, no crash."""
        df = pd.DataFrame(columns=["open", "high", "low", "close"])
        result = compute_indicators(df)
        assert result.ema_20 is None
        assert result.rsi_14 is None
        assert result.macd_line is None
        assert result.atr_14 is None
        assert result.bb_upper is None
        assert result.trend == "neutral"

    def test_single_candle_returns_defaults(self):
        """Single row → all indicators None, no crash."""
        df = pd.DataFrame(
            [{"open": 1.1, "high": 1.11, "low": 1.09, "close": 1.10}]
        )
        result = compute_indicators(df)
        assert result.ema_20 is None
        assert result.rsi_14 is None
        assert result.trend == "neutral"

    def test_none_dataframe_returns_defaults(self):
        result = compute_indicators(None)
        assert result.ema_20 is None
        assert result.trend == "neutral"
