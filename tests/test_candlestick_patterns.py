"""Unit tests for candlestick pattern detectors.

Each test crafts a small OHLC DataFrame triggering a specific pattern and
verifies correct detection, direction, and candle_index.  False-positive
tests verify non-matching data produces no patterns.
"""

from __future__ import annotations

import pandas as pd
import pytest

from forexmind.agents.candlestick.patterns import (
    detect_doji,
    detect_engulfing,
    detect_evening_star,
    detect_hammer,
    detect_hanging_man,
    detect_harami,
    detect_marubozu,
    detect_morning_star,
    detect_shooting_star,
    detect_spinning_top,
    detect_three_black_crows,
    detect_three_white_soldiers,
    detect_tweezer_bottom,
    detect_tweezer_top,
    detect_all_patterns,
)


def _make_df(candles: list[dict]) -> pd.DataFrame:
    """Helper: build a DataFrame from a list of OHLC dicts."""
    for i, c in enumerate(candles):
        c.setdefault("timestamp", f"2024-01-{i + 1:02d}")
    return pd.DataFrame(candles)


# ═══════════════════════════════════════════════════════════════════════════
# Single-candle patterns
# ═══════════════════════════════════════════════════════════════════════════


class TestHammer:
    def test_detects_hammer(self):
        """Small body near top, long lower wick."""
        df = _make_df([
            {"open": 1.1000, "high": 1.1010, "low": 1.0900, "close": 1.1005},
        ])
        patterns = detect_hammer(df)
        assert len(patterns) == 1
        assert patterns[0].name == "hammer"
        assert patterns[0].direction == "bullish"
        assert patterns[0].candle_index == 0

    def test_no_hammer_on_marubozu(self):
        """Full-body candle should not match."""
        df = _make_df([
            {"open": 1.1000, "high": 1.1100, "low": 1.1000, "close": 1.1100},
        ])
        assert detect_hammer(df) == []


class TestHangingMan:
    def test_detects_hanging_man_after_uptrend(self):
        """Same shape as hammer but preceded by 3 rising closes."""
        df = _make_df([
            {"open": 1.0900, "high": 1.0920, "low": 1.0890, "close": 1.0910},
            {"open": 1.0910, "high": 1.0940, "low": 1.0905, "close": 1.0930},
            {"open": 1.0930, "high": 1.0960, "low": 1.0925, "close": 1.0950},
            # Hanging man candle
            {"open": 1.0955, "high": 1.0960, "low": 1.0850, "close": 1.0950},
        ])
        patterns = detect_hanging_man(df)
        assert len(patterns) == 1
        assert patterns[0].name == "hanging_man"
        assert patterns[0].direction == "bearish"
        assert patterns[0].candle_index == 3

    def test_no_hanging_man_without_uptrend(self):
        """Same shape but no prior uptrend → no hanging man."""
        df = _make_df([
            {"open": 1.0950, "high": 1.0960, "low": 1.0940, "close": 1.0930},
            {"open": 1.0930, "high": 1.0935, "low": 1.0910, "close": 1.0920},
            {"open": 1.0920, "high": 1.0925, "low": 1.0900, "close": 1.0910},
            {"open": 1.0915, "high": 1.0920, "low": 1.0810, "close": 1.0910},
        ])
        assert detect_hanging_man(df) == []


class TestDoji:
    def test_detects_doji(self):
        """Body ≤ 10% of total range."""
        df = _make_df([
            {"open": 1.1000, "high": 1.1050, "low": 1.0950, "close": 1.1001},
        ])
        patterns = detect_doji(df)
        assert len(patterns) == 1
        assert patterns[0].name == "doji"
        assert patterns[0].direction == "neutral"

    def test_no_doji_on_large_body(self):
        df = _make_df([
            {"open": 1.1000, "high": 1.1060, "low": 1.0990, "close": 1.1050},
        ])
        assert detect_doji(df) == []


class TestShootingStar:
    def test_detects_shooting_star(self):
        """Small body at bottom, long upper wick."""
        df = _make_df([
            {"open": 1.1005, "high": 1.1100, "low": 1.0995, "close": 1.1000},
        ])
        patterns = detect_shooting_star(df)
        assert len(patterns) == 1
        assert patterns[0].name == "shooting_star"
        assert patterns[0].direction == "bearish"

    def test_no_shooting_star_on_hammer_shape(self):
        """Hammer shape (long lower wick) should not match."""
        df = _make_df([
            {"open": 1.1000, "high": 1.1010, "low": 1.0900, "close": 1.1005},
        ])
        assert detect_shooting_star(df) == []


class TestMarubozu:
    def test_detects_bullish_marubozu(self):
        """Full bullish candle with negligible wicks."""
        df = _make_df([
            {"open": 1.1000, "high": 1.1100, "low": 1.1000, "close": 1.1100},
        ])
        patterns = detect_marubozu(df)
        assert len(patterns) == 1
        assert patterns[0].direction == "bullish"

    def test_detects_bearish_marubozu(self):
        df = _make_df([
            {"open": 1.1100, "high": 1.1100, "low": 1.1000, "close": 1.1000},
        ])
        patterns = detect_marubozu(df)
        assert len(patterns) == 1
        assert patterns[0].direction == "bearish"


class TestSpinningTop:
    def test_detects_spinning_top(self):
        """Small body with balanced wicks."""
        df = _make_df([
            {"open": 1.1000, "high": 1.1040, "low": 1.0960, "close": 1.1010},
        ])
        patterns = detect_spinning_top(df)
        assert len(patterns) == 1
        assert patterns[0].name == "spinning_top"
        assert patterns[0].direction == "neutral"


# ═══════════════════════════════════════════════════════════════════════════
# Multi-candle patterns
# ═══════════════════════════════════════════════════════════════════════════


class TestEngulfing:
    def test_bullish_engulfing(self):
        """Bearish candle followed by larger bullish candle."""
        df = _make_df([
            {"open": 1.1020, "high": 1.1025, "low": 1.0995, "close": 1.1000},
            {"open": 1.0990, "high": 1.1035, "low": 1.0985, "close": 1.1030},
        ])
        patterns = detect_engulfing(df)
        assert len(patterns) == 1
        assert patterns[0].name == "bullish_engulfing"
        assert patterns[0].direction == "bullish"
        assert patterns[0].candle_index == 1

    def test_bearish_engulfing(self):
        """Bullish candle followed by larger bearish candle."""
        df = _make_df([
            {"open": 1.1000, "high": 1.1025, "low": 1.0995, "close": 1.1020},
            {"open": 1.1030, "high": 1.1035, "low": 1.0985, "close": 1.0990},
        ])
        patterns = detect_engulfing(df)
        assert len(patterns) == 1
        assert patterns[0].name == "bearish_engulfing"
        assert patterns[0].direction == "bearish"

    def test_no_engulfing_same_direction(self):
        """Two bullish candles → no engulfing."""
        df = _make_df([
            {"open": 1.1000, "high": 1.1025, "low": 1.0995, "close": 1.1020},
            {"open": 1.1020, "high": 1.1050, "low": 1.1015, "close": 1.1045},
        ])
        assert detect_engulfing(df) == []


class TestHarami:
    def test_bullish_harami(self):
        """Large bearish candle, small bullish candle inside."""
        df = _make_df([
            {"open": 1.1050, "high": 1.1060, "low": 1.0980, "close": 1.0990},
            {"open": 1.1000, "high": 1.1030, "low": 1.0995, "close": 1.1020},
        ])
        patterns = detect_harami(df)
        assert len(patterns) == 1
        assert patterns[0].name == "bullish_harami"
        assert patterns[0].direction == "bullish"

    def test_bearish_harami(self):
        """Large bullish candle, small bearish candle inside."""
        df = _make_df([
            {"open": 1.0990, "high": 1.1060, "low": 1.0980, "close": 1.1050},
            {"open": 1.1040, "high": 1.1045, "low": 1.1000, "close": 1.1010},
        ])
        patterns = detect_harami(df)
        assert len(patterns) == 1
        assert patterns[0].name == "bearish_harami"


class TestMorningStar:
    def test_detects_morning_star(self):
        """3-candle bullish reversal."""
        df = _make_df([
            # Large bearish
            {"open": 1.1050, "high": 1.1055, "low": 1.0950, "close": 1.0960},
            # Small body
            {"open": 1.0960, "high": 1.0975, "low": 1.0945, "close": 1.0955},
            # Large bullish closing above midpoint of candle 1
            {"open": 1.0960, "high": 1.1040, "low": 1.0955, "close": 1.1030},
        ])
        patterns = detect_morning_star(df)
        assert len(patterns) == 1
        assert patterns[0].name == "morning_star"
        assert patterns[0].direction == "bullish"
        assert patterns[0].candle_index == 2


class TestEveningStar:
    def test_detects_evening_star(self):
        """3-candle bearish reversal."""
        df = _make_df([
            # Large bullish
            {"open": 1.0960, "high": 1.1055, "low": 1.0955, "close": 1.1050},
            # Small body
            {"open": 1.1050, "high": 1.1065, "low": 1.1040, "close": 1.1055},
            # Large bearish closing below midpoint of candle 1
            {"open": 1.1040, "high": 1.1045, "low": 1.0950, "close": 1.0960},
        ])
        patterns = detect_evening_star(df)
        assert len(patterns) == 1
        assert patterns[0].name == "evening_star"
        assert patterns[0].direction == "bearish"


class TestThreeWhiteSoldiers:
    def test_detects_pattern(self):
        """3 consecutive bullish candles, each opening within prior body,
        each closing higher."""
        df = _make_df([
            {"open": 1.1000, "high": 1.1050, "low": 1.0995, "close": 1.1040},
            {"open": 1.1020, "high": 1.1080, "low": 1.1015, "close": 1.1070},
            {"open": 1.1050, "high": 1.1120, "low": 1.1045, "close": 1.1110},
        ])
        patterns = detect_three_white_soldiers(df)
        assert len(patterns) == 1
        assert patterns[0].direction == "bullish"


class TestThreeBlackCrows:
    def test_detects_pattern(self):
        """3 consecutive bearish candles, each opening within prior body,
        each closing lower."""
        df = _make_df([
            {"open": 1.1110, "high": 1.1120, "low": 1.1045, "close": 1.1050},
            {"open": 1.1070, "high": 1.1080, "low": 1.1015, "close": 1.1020},
            {"open": 1.1040, "high": 1.1050, "low": 1.0995, "close": 1.1000},
        ])
        patterns = detect_three_black_crows(df)
        assert len(patterns) == 1
        assert patterns[0].direction == "bearish"


class TestTweezerTop:
    def test_detects_tweezer_top(self):
        """Bullish then bearish with matching highs."""
        df = _make_df([
            {"open": 1.1000, "high": 1.1050, "low": 1.0990, "close": 1.1040},
            {"open": 1.1040, "high": 1.1050, "low": 1.0990, "close": 1.1000},
        ])
        patterns = detect_tweezer_top(df)
        assert len(patterns) == 1
        assert patterns[0].direction == "bearish"


class TestTweezerBottom:
    def test_detects_tweezer_bottom(self):
        """Bearish then bullish with matching lows."""
        df = _make_df([
            {"open": 1.1040, "high": 1.1050, "low": 1.0990, "close": 1.1000},
            {"open": 1.1000, "high": 1.1050, "low": 1.0990, "close": 1.1040},
        ])
        patterns = detect_tweezer_bottom(df)
        assert len(patterns) == 1
        assert patterns[0].direction == "bullish"


# ═══════════════════════════════════════════════════════════════════════════
# Top-level runner
# ═══════════════════════════════════════════════════════════════════════════


class TestDetectAllPatterns:
    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])
        assert detect_all_patterns(df) == []

    def test_returns_sorted_by_index(self):
        """Patterns from different detectors should be sorted by candle_index."""
        df = _make_df([
            # Doji at index 0
            {"open": 1.1000, "high": 1.1050, "low": 1.0950, "close": 1.1001},
            # Marubozu at index 1
            {"open": 1.1000, "high": 1.1100, "low": 1.1000, "close": 1.1100},
        ])
        patterns = detect_all_patterns(df)
        assert len(patterns) >= 2
        indices = [p.candle_index for p in patterns]
        assert indices == sorted(indices)
