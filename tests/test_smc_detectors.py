"""Unit tests for SMC / ICT detectors.

Tests FVG detection, Order Block identification, Market Structure shifts (BOS/CHOCH),
Liquidity Pools, and Dealing Range calculation.
"""

from __future__ import annotations

import pandas as pd
import pytest

from forexmind.agents.smc.detectors import (
    detect_fvgs,
    detect_market_structure_and_obs,
    detect_liquidity_and_sweeps,
    calculate_dealing_range,
    analyze_smc,
)


def _make_df(candles: list[dict]) -> pd.DataFrame:
    for i, c in enumerate(candles):
        if "timestamp" not in c:
            c["timestamp"] = f"2024-01-{i + 1:02d}"
    return pd.DataFrame(candles)


class TestFVG:
    def test_bullish_fvg(self):
        df = _make_df([
            {"high": 1.1000, "low": 1.0990, "open": 1.0995, "close": 1.1000},
            {"high": 1.1030, "low": 1.0995, "open": 1.1000, "close": 1.1025},
            {"high": 1.1050, "low": 1.1015, "open": 1.1025, "close": 1.1040},
        ])
        fvgs = detect_fvgs(df)
        assert len(fvgs) == 1
        assert fvgs[0].direction == "bullish"
        assert fvgs[0].bottom == 1.1000
        assert fvgs[0].top == 1.1015
        assert not fvgs[0].mitigated

    def test_bearish_fvg_mitigated(self):
        df = _make_df([
            {"high": 1.1050, "low": 1.1020, "open": 1.1040, "close": 1.1030},
            {"high": 1.1035, "low": 1.0980, "open": 1.1030, "close": 1.0990},
            {"high": 1.1005, "low": 1.0970, "open": 1.0990, "close": 1.0980},
            {"high": 1.1030, "low": 1.0970, "open": 1.0980, "close": 1.1025}, # mitigates
        ])
        fvgs = detect_fvgs(df)
        assert len(fvgs) == 1
        assert fvgs[0].direction == "bearish"
        assert fvgs[0].top == 1.1020
        assert fvgs[0].bottom == 1.1005
        assert fvgs[0].mitigated


class TestLiquidity:
    def test_eqh_and_sweep(self):
        rows = []
        for i in range(30):
            high = 1.1000
            low = 1.0980
            close = 1.0990
            
            if i == 5:
                high = 1.1050
            if i == 15:
                high = 1.1050
            if i == 25:
                # Sweep: huge wick
                high = 1.1060
                low = 1.1030
                close = 1.1040
                open_ = 1.1035
            else:
                open_ = 1.0990
                
            rows.append({"open": open_, "high": high, "low": low, "close": close})
            
        df = _make_df(rows)
        pools, sweeps = detect_liquidity_and_sweeps(df)
        
        eqhs = [p for p in pools if p.type == "EQH"]
        assert len(eqhs) > 0
        assert len(sweeps) > 0
        assert sweeps[0].pool_type == "EQH"


class TestMarketStructure:
    def test_bos_and_ob(self):
        rows = []
        for i in range(50):
            val = 1.1000 + i * 0.0010
            
            if 10 < i <= 20: # pullback
                val = 1.1000 + 10 * 0.0010 - (i - 10) * 0.0010
            elif 20 < i <= 35: # impulse up past 10
                val = 1.1000 + (i - 20) * 0.0020
            elif i > 35: # pullback to form swing high at 35
                val = 1.1000 + 15 * 0.0020 - (i - 35) * 0.0010
                
            open_ = val
            close = val + 0.0001 if i <= 10 or (20 < i <= 35) else val - 0.0001
            high = max(open_, close) + 0.0001
            low = min(open_, close) - 0.0001
            
            rows.append({"open": open_, "high": high, "low": low, "close": close})
            
        df = _make_df(rows)
        shifts, obs = detect_market_structure_and_obs(df)
        
        bos = [s for s in shifts if s.type == "BOS" and s.direction == "bullish"]
        assert len(bos) > 0
        assert len(obs) > 0


class TestDealingRange:
    def test_range_calculation(self):
        rows = []
        # Create a swing low at 15
        for i in range(16):
            val = 1.1200 - i * 0.0010
            rows.append({"open": val, "high": val + 0.0001, "low": val - 0.0001, "close": val})
        
        # Create a swing high at 45 (1.1050 + 30*0.001 = 1.1350)
        for i in range(16, 46):
            val = 1.1050 + (i - 15) * 0.0010
            rows.append({"open": val, "high": val + 0.0001, "low": val - 0.0001, "close": val})
            
        # Pullback to form the swing high at 45
        for i in range(46, 60):
            val = 1.1350 - (i - 45) * 0.0010
            rows.append({"open": val, "high": val + 0.0001, "low": val - 0.0001, "close": val})
            
        df = _make_df(rows)
        dr = calculate_dealing_range(df)
        
        assert dr is not None
        assert dr.swing_high == pytest.approx(1.1351)
        assert dr.swing_low == pytest.approx(1.1049)
