"""Unit tests for Support & Resistance detectors.

Tests clustering of swing points into horizontal levels, detection of psychological
levels, and calculation of dynamic EMAs.
"""

from __future__ import annotations

import pandas as pd
import pytest

from forexmind.agents.support_resistance.detectors import (
    _cluster_points,
    detect_horizontal_levels,
    detect_psychological_levels,
    detect_dynamic_levels,
    analyze_support_resistance,
)


def _make_df(candles: list[dict]) -> pd.DataFrame:
    for i, c in enumerate(candles):
        c.setdefault("timestamp", f"2024-01-{i + 1:02d}")
    return pd.DataFrame(candles)


class TestClustering:
    def test_empty_points(self):
        assert _cluster_points([], 0.0010) == []

    def test_single_point(self):
        clusters = _cluster_points([1.1000], 0.0010)
        assert len(clusters) == 1
        assert clusters[0]["price"] == 1.1000
        assert clusters[0]["touches"] == 1

    def test_clusters_within_tolerance(self):
        points = [1.1000, 1.1005, 1.1009]
        clusters = _cluster_points(points, 0.0010)
        assert len(clusters) == 1
        assert clusters[0]["touches"] == 3
        # Average of 1.1000, 1.1005, 1.1009 is 1.100466...
        assert clusters[0]["price"] == pytest.approx(1.100466, abs=1e-5)
        assert clusters[0]["high"] == 1.1009
        assert clusters[0]["low"] == 1.1000

    def test_separates_clusters_outside_tolerance(self):
        points = [1.1000, 1.1005, 1.1020, 1.1025]
        clusters = _cluster_points(points, 0.0010)
        # Should be two clusters: [1.1025, 1.1020] and [1.1005, 1.1000]
        assert len(clusters) == 2
        
        c1 = clusters[0]  # The higher one
        assert c1["touches"] == 2
        assert c1["price"] == pytest.approx(1.10225)
        
        c2 = clusters[1]  # The lower one
        assert c2["touches"] == 2
        assert c2["price"] == pytest.approx(1.10025)


class TestPsychologicalLevels:
    def test_detects_near_round_numbers(self):
        current_price = 1.1005
        sup, res = detect_psychological_levels(current_price, interval=0.0050, proximity=0.0020)
        
        # Lower is 1.1000, Upper is 1.1050
        assert len(sup) == 1
        assert len(res) == 1
        
        assert sup[0].price == 1.1000
        assert res[0].price == 1.1050
        
        # 1.1000 is within 20 pips (0.0020) of 1.1005, so it's moderate
        assert sup[0].strength == "moderate"
        
        # 1.1050 is 45 pips away, so it's weak
        assert res[0].strength == "weak"


class TestDynamicLevels:
    def test_calculates_emas_and_classifies_correctly(self):
        # Create a linear uptrend so EMAs will be below current price (acting as support)
        rows = [
            {"open": 1.1000 + i*0.0010, "high": 1.1005 + i*0.0010, "low": 1.0995 + i*0.0010, "close": 1.1000 + i*0.0010}
            for i in range(210)
        ]
        df = _make_df(rows)
        current_price = df["close"].iloc[-1]
        
        sup, res = detect_dynamic_levels(df, current_price)
        
        # Both 50 EMA and 200 EMA should be calculated and be supports
        assert len(sup) == 2
        assert len(res) == 0
        
        sources = [s.source for s in sup]
        assert "EMA_50" in sources
        assert "EMA_200" in sources
        
        ema_200 = next(s for s in sup if s.source == "EMA_200")
        assert ema_200.strength == "moderate"
        
        ema_50 = next(s for s in sup if s.source == "EMA_50")
        assert ema_50.strength == "weak"

    def test_skips_emas_if_insufficient_data(self):
        df = _make_df([{"open": 1.1, "high": 1.2, "low": 1.0, "close": 1.15}] * 100)
        sup, res = detect_dynamic_levels(df, 1.15)
        
        # Only 50 EMA should be present
        assert len(sup) + len(res) == 1
        level = (sup + res)[0]
        assert level.source == "EMA_50"


class TestAnalyzeSupportResistance:
    def test_end_to_end_analysis(self):
        # Simple oscillating data to create swing points
        import math
        rows = []
        for i in range(100):
            val = 1.1000 + 0.0050 * math.sin(i * math.pi / 5)
            rows.append({"open": val, "high": val + 0.0005, "low": val - 0.0005, "close": val})
            
        df = _make_df(rows)
        result = analyze_support_resistance(df)
        
        assert isinstance(result.support_levels, list)
        assert isinstance(result.resistance_levels, list)
        
        # Check sorting: supports descending, resistances ascending
        if len(result.support_levels) >= 2:
            assert result.support_levels[0].price >= result.support_levels[1].price
        if len(result.resistance_levels) >= 2:
            assert result.resistance_levels[0].price <= result.resistance_levels[1].price
