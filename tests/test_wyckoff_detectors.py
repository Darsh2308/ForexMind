import pandas as pd

from forexmind.agents.wyckoff.detectors import _detect_phase, _detect_events, analyze_wyckoff


def test_wyckoff_accumulation_phase():
    # Simulate a markdown followed by a range near the lows
    # 100 candles of markdown, 50 candles ranging
    data = []
    # Markdown
    for i in range(100):
        data.append({"close": 1.5 - i * 0.005, "high": 1.5 - i * 0.005 + 0.001, "low": 1.5 - i * 0.005 - 0.001})
    
    # Ranging near 1.0
    for i in range(49):
        data.append({"close": 1.0 + (i % 2) * 0.01, "high": 1.02, "low": 0.99})
    # Final candle closes near the low to trigger accumulation heuristic (< 0.3 of range)
    data.append({"close": 0.991, "high": 1.02, "low": 0.99})
        
    df = pd.DataFrame(data)
    phase = _detect_phase(df)
    
    assert phase.phase == "accumulation"
    assert phase.support_level == 0.99
    assert phase.resistance_level == 1.02


def test_wyckoff_distribution_phase():
    # Simulate a markup followed by a range near the highs
    # 100 candles of markup, 50 candles ranging
    data = []
    # Markup
    for i in range(100):
        data.append({"close": 1.0 + i * 0.005, "high": 1.0 + i * 0.005 + 0.001, "low": 1.0 + i * 0.005 - 0.001})
    
    # Ranging near 1.5
    for i in range(49):
        data.append({"close": 1.5 + (i % 2) * 0.01, "high": 1.52, "low": 1.49})
    # Final candle closes near the high to trigger distribution heuristic (> 0.7 of range)
    data.append({"close": 1.515, "high": 1.52, "low": 1.49})
        
    df = pd.DataFrame(data)
    phase = _detect_phase(df)
    
    assert phase.phase == "distribution"
    assert phase.support_level == 1.49
    assert phase.resistance_level == 1.52


def test_analyze_empty_df():
    df = pd.DataFrame()
    res = analyze_wyckoff(df)
    assert res.current_phase.phase == "unknown"
    assert len(res.events) == 0
