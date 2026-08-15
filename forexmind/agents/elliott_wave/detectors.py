from __future__ import annotations

import pandas as pd

from forexmind.agents.elliott_wave.schemas import ElliottWaveResult, Wave, WaveCount
from forexmind.agents.price_action.detectors import (
    find_swing_highs,
    find_swing_lows,
    PIVOT_ORDER,
)

# A simple rule-based approach: we look for the last 6 swing points
# to form a 5-wave motive sequence (0->1, 1->2, 2->3, 3->4, 4->5).


def _get_ordered_pivots(df: pd.DataFrame) -> list[dict]:
    """Get a time-ordered sequence of alternating swing highs and lows."""
    if df.empty:
        return []

    swing_highs = find_swing_highs(df["high"], order=PIVOT_ORDER)
    swing_lows = find_swing_lows(df["low"], order=PIVOT_ORDER)

    pivots = []
    for idx, val in swing_highs:
        pivots.append({"index": idx, "price": val, "type": "high"})
    for idx, val in swing_lows:
        pivots.append({"index": idx, "price": val, "type": "low"})

    # Sort by index
    pivots.sort(key=lambda x: x["index"])

    # Basic cleanup: if there are consecutive highs or consecutive lows, keep the extreme
    filtered_pivots = []
    for p in pivots:
        if not filtered_pivots:
            filtered_pivots.append(p)
        else:
            last = filtered_pivots[-1]
            if last["type"] == p["type"]:
                if last["type"] == "high" and p["price"] > last["price"]:
                    filtered_pivots[-1] = p
                elif last["type"] == "low" and p["price"] < last["price"]:
                    filtered_pivots[-1] = p
            else:
                filtered_pivots.append(p)

    return filtered_pivots


def _check_bullish_motive(pivots: list[dict]) -> WaveCount | None:
    """Check if the last 6 pivots form a bullish 5-wave motive pattern."""
    if len(pivots) < 6:
        return None

    # Try matching the last 6 pivots to [Low, High, Low, High, Low, High]
    # Representing [Start of W1, End of W1, End of W2, End of W3, End of W4, End of W5]
    p = pivots[-6:]
    if p[0]["type"] != "low":
        return None

    w1_start = p[0]["price"]
    w1_end = p[1]["price"]
    w2_end = p[2]["price"]
    w3_end = p[3]["price"]
    w4_end = p[4]["price"]
    w5_end = p[5]["price"]

    # Rule 1: Wave 2 never moves beyond the start of Wave 1
    if w2_end <= w1_start:
        return None

    # Rule 2: Wave 3 is never the shortest among 1, 3, and 5
    w1_len = w1_end - w1_start
    w3_len = w3_end - w2_end
    w5_len = w5_end - w4_end
    if w3_len <= w1_len and w3_len <= w5_len:
        return None

    # Rule 3: Wave 4 does not overlap Wave 1
    if w4_end <= w1_end:
        return None

    # Needs to make higher highs (W3 > W1, W5 > W3 is typical)
    if w3_end <= w1_end or w5_end <= w3_end:
        return None

    waves = [
        Wave(label="1", start_index=p[0]["index"], end_index=p[1]["index"], start_price=w1_start, end_price=w1_end),
        Wave(label="2", start_index=p[1]["index"], end_index=p[2]["index"], start_price=w1_end, end_price=w2_end),
        Wave(label="3", start_index=p[2]["index"], end_index=p[3]["index"], start_price=w2_end, end_price=w3_end),
        Wave(label="4", start_index=p[3]["index"], end_index=p[4]["index"], start_price=w3_end, end_price=w4_end),
        Wave(label="5", start_index=p[4]["index"], end_index=p[5]["index"], start_price=w4_end, end_price=w5_end),
    ]

    return WaveCount(
        pattern_type="motive",
        degree="minor",
        waves=waves,
        confidence=0.7,  # Basic confidence since it passed strict rules
        is_valid=True,
    )


def _check_bearish_motive(pivots: list[dict]) -> WaveCount | None:
    """Check if the last 6 pivots form a bearish 5-wave motive pattern."""
    if len(pivots) < 6:
        return None

    # [High, Low, High, Low, High, Low]
    p = pivots[-6:]
    if p[0]["type"] != "high":
        return None

    w1_start = p[0]["price"]
    w1_end = p[1]["price"]
    w2_end = p[2]["price"]
    w3_end = p[3]["price"]
    w4_end = p[4]["price"]
    w5_end = p[5]["price"]

    # Rule 1: Wave 2 never moves beyond the start of Wave 1
    if w2_end >= w1_start:
        return None

    # Rule 2: Wave 3 is never the shortest
    w1_len = w1_start - w1_end
    w3_len = w2_end - w3_end
    w5_len = w4_end - w5_end
    if w3_len <= w1_len and w3_len <= w5_len:
        return None

    # Rule 3: Wave 4 does not overlap Wave 1
    if w4_end >= w1_end:
        return None

    if w3_end >= w1_end or w5_end >= w3_end:
        return None

    waves = [
        Wave(label="1", start_index=p[0]["index"], end_index=p[1]["index"], start_price=w1_start, end_price=w1_end),
        Wave(label="2", start_index=p[1]["index"], end_index=p[2]["index"], start_price=w1_end, end_price=w2_end),
        Wave(label="3", start_index=p[2]["index"], end_index=p[3]["index"], start_price=w2_end, end_price=w3_end),
        Wave(label="4", start_index=p[3]["index"], end_index=p[4]["index"], start_price=w3_end, end_price=w4_end),
        Wave(label="5", start_index=p[4]["index"], end_index=p[5]["index"], start_price=w4_end, end_price=w5_end),
    ]

    return WaveCount(
        pattern_type="motive",
        degree="minor",
        waves=waves,
        confidence=0.7,
        is_valid=True,
    )


def analyze_elliott_wave(df: pd.DataFrame) -> ElliottWaveResult:
    """Analyze price data to detect Elliott Wave structures."""
    if df.empty or len(df) < PIVOT_ORDER * 2:
        return ElliottWaveResult()

    pivots = _get_ordered_pivots(df)
    
    # Try finding a motive wave pattern
    bullish_count = _check_bullish_motive(pivots)
    if bullish_count:
        return ElliottWaveResult(current_count=bullish_count)

    bearish_count = _check_bearish_motive(pivots)
    if bearish_count:
        return ElliottWaveResult(current_count=bearish_count)

    return ElliottWaveResult()
