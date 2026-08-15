import pandas as pd

from forexmind.agents.elliott_wave.detectors import _check_bullish_motive, _check_bearish_motive, analyze_elliott_wave


def test_bullish_motive_detection():
    # Construct an ideal bullish 5-wave sequence in pivot form
    # Start(W1), End(W1), End(W2), End(W3), End(W4), End(W5)
    pivots = [
        {"index": 1, "price": 1.0, "type": "low"},   # start
        {"index": 2, "price": 1.2, "type": "high"},  # w1 end
        {"index": 3, "price": 1.1, "type": "low"},   # w2 end
        {"index": 4, "price": 1.5, "type": "high"},  # w3 end
        {"index": 5, "price": 1.3, "type": "low"},   # w4 end
        {"index": 6, "price": 1.6, "type": "high"},  # w5 end
    ]
    
    res = _check_bullish_motive(pivots)
    assert res is not None
    assert res.pattern_type == "motive"
    assert len(res.waves) == 5
    assert res.is_valid is True


def test_bullish_motive_invalidation_rule_4():
    # Wave 4 overlaps Wave 1 (w4_end < w1_end)
    pivots = [
        {"index": 1, "price": 1.0, "type": "low"},
        {"index": 2, "price": 1.2, "type": "high"},
        {"index": 3, "price": 1.1, "type": "low"},
        {"index": 4, "price": 1.5, "type": "high"},
        {"index": 5, "price": 1.15, "type": "low"},  # W4 overlaps W1
        {"index": 6, "price": 1.6, "type": "high"},
    ]
    
    res = _check_bullish_motive(pivots)
    assert res is None


def test_bearish_motive_detection():
    pivots = [
        {"index": 1, "price": 1.6, "type": "high"},
        {"index": 2, "price": 1.4, "type": "low"},
        {"index": 3, "price": 1.5, "type": "high"},
        {"index": 4, "price": 1.1, "type": "low"},
        {"index": 5, "price": 1.3, "type": "high"},
        {"index": 6, "price": 1.0, "type": "low"},
    ]
    
    res = _check_bearish_motive(pivots)
    assert res is not None
    assert res.pattern_type == "motive"
    assert len(res.waves) == 5
    assert res.is_valid is True


def test_analyze_empty_df():
    df = pd.DataFrame()
    res = analyze_elliott_wave(df)
    assert res.current_count.pattern_type == "none"
