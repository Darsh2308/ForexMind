"""Pure price-action detection — no I/O, no state.

Every public function takes a pandas DataFrame with OHLC columns
(``open``, ``high``, ``low``, ``close``, ``timestamp``) sorted
chronologically (oldest first) and returns structured price-action
analysis results.

All detection is mathematical — no LLM.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from forexmind.agents.price_action.schemas import (
    BreakoutSignal,
    PriceActionResult,
    PullbackSignal,
    RangeState,
    RejectionSignal,
    TrendState,
)

logger = logging.getLogger(__name__)

# ── Configurable parameters ─────────────────────────────────────────────────
# Swing-point detection: a pivot high/low must have this many bars on each
# side that are lower/higher.
PIVOT_ORDER = 2

# Minimum bars needed for trend classification
MIN_BARS_TREND = 10

# Breakout: price must exceed the level by at least this fraction of ATR
# (if ATR is available) or this absolute amount.
BREAKOUT_ATR_FRACTION = 0.5
BREAKOUT_ABS_THRESHOLD = 0.0005  # ~5 pips

# Range detection: if price stays within this fraction of the range for
# N bars, it's considered ranging.
RANGE_THRESHOLD_RATIO = 0.02  # 2% of midprice
RANGE_MIN_BARS = 10

# Rejection: wick must be at least this multiple of the body.
REJECTION_WICK_MULTIPLE = 2.0

# Pullback: minimum depth as fraction of prior move to count
PULLBACK_MIN_DEPTH = 0.20  # 20%
PULLBACK_MAX_DEPTH = 0.80  # 80% (beyond this, it's likely a reversal)


def find_swing_highs(
    highs: pd.Series, order: int = PIVOT_ORDER
) -> list[tuple[int, float]]:
    """Find swing highs (local maxima).  Returns list of (index, value)."""
    swings: list[tuple[int, float]] = []
    n = len(highs)
    for i in range(order, n - order):
        is_swing = True
        for j in range(1, order + 1):
            if highs.iloc[i] <= highs.iloc[i - j] or highs.iloc[i] <= highs.iloc[i + j]:
                is_swing = False
                break
        if is_swing:
            swings.append((i, float(highs.iloc[i])))
    return swings


def find_swing_lows(
    lows: pd.Series, order: int = PIVOT_ORDER
) -> list[tuple[int, float]]:
    """Find swing lows (local minima).  Returns list of (index, value)."""
    swings: list[tuple[int, float]] = []
    n = len(lows)
    for i in range(order, n - order):
        is_swing = True
        for j in range(1, order + 1):
            if lows.iloc[i] >= lows.iloc[i - j] or lows.iloc[i] >= lows.iloc[i + j]:
                is_swing = False
                break
        if is_swing:
            swings.append((i, float(lows.iloc[i])))
    return swings


def classify_trend(df: pd.DataFrame, lookback: int = 20) -> TrendState:
    """Classify trend based on swing-point structure over the last
    ``lookback`` bars.

    Examines sequences of swing highs and swing lows to determine:
    - HH/HL → bullish
    - LH/LL → bearish
    - Mixed → ranging

    Falls back to comparing start/end closes when data is monotonic
    (no swing points found — a sign of a very strong trend).
    """
    if len(df) < MIN_BARS_TREND:
        return TrendState()

    # Use the most recent `lookback` bars (but swing detection needs a buffer)
    window_start = max(0, len(df) - lookback - PIVOT_ORDER)
    window = df.iloc[window_start:].reset_index(drop=True)

    swing_highs = find_swing_highs(window["high"], order=PIVOT_ORDER)
    swing_lows = find_swing_lows(window["low"], order=PIVOT_ORDER)

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        # Fallback: not enough swing points — use simple close comparison
        # This handles monotonic trends (perfectly rising or falling).
        first_close = float(window["close"].iloc[0])
        last_close = float(window["close"].iloc[-1])
        mid_close = float(window["close"].iloc[len(window) // 2])
        delta = last_close - first_close
        total_range = float(window["high"].max() - window["low"].min())

        if total_range > 0 and abs(delta) / total_range > 0.3:
            if delta > 0 and last_close > mid_close:
                return TrendState(
                    direction="bullish",
                    strength="moderate",
                    higher_highs=True,
                    higher_lows=True,
                )
            elif delta < 0 and last_close < mid_close:
                return TrendState(
                    direction="bearish",
                    strength="moderate",
                    lower_highs=True,
                    lower_lows=True,
                )
        return TrendState(direction="ranging", strength="weak")

    # Check last 2-3 swing points for structure
    recent_highs = [v for _, v in swing_highs[-3:]]
    recent_lows = [v for _, v in swing_lows[-3:]]

    hh = all(recent_highs[i] > recent_highs[i - 1] for i in range(1, len(recent_highs)))
    hl = all(recent_lows[i] > recent_lows[i - 1] for i in range(1, len(recent_lows)))
    lh = all(recent_highs[i] < recent_highs[i - 1] for i in range(1, len(recent_highs)))
    ll = all(recent_lows[i] < recent_lows[i - 1] for i in range(1, len(recent_lows)))

    if hh and hl:
        direction = "bullish"
        strength = "strong" if len(recent_highs) >= 3 else "moderate"
    elif lh and ll:
        direction = "bearish"
        strength = "strong" if len(recent_lows) >= 3 else "moderate"
    else:
        direction = "ranging"
        strength = "weak"

    return TrendState(
        direction=direction,
        strength=strength,
        higher_highs=hh,
        higher_lows=hl,
        lower_highs=lh,
        lower_lows=ll,
    )


def detect_breakouts(
    df: pd.DataFrame, lookback: int = 20
) -> list[BreakoutSignal]:
    """Detect breakouts: price breaking above recent resistance or below
    recent support within the last few candles.

    Uses swing highs as resistance and swing lows as support.
    """
    if len(df) < MIN_BARS_TREND:
        return []

    signals: list[BreakoutSignal] = []

    # Identify swing points from the lookback window (excluding the last
    # few candles which are the candidate breakout bars)
    analysis_end = len(df) - 1
    window_start = max(0, analysis_end - lookback - PIVOT_ORDER)
    window = df.iloc[window_start : analysis_end - 2]  # exclude last 2 bars

    if len(window) < MIN_BARS_TREND:
        return []

    swing_highs = find_swing_highs(window["high"], order=PIVOT_ORDER)
    swing_lows = find_swing_lows(window["low"], order=PIVOT_ORDER)

    # Calculate a simple ATR proxy for threshold
    recent = df.iloc[-lookback:]
    avg_range = (recent["high"] - recent["low"]).mean()
    threshold = max(avg_range * BREAKOUT_ATR_FRACTION, BREAKOUT_ABS_THRESHOLD)

    # Check if the most recent candle broke above the highest recent swing high
    if swing_highs:
        resistance = max(v for _, v in swing_highs[-3:])
        last = df.iloc[-1]
        if last["close"] > resistance + threshold:
            signals.append(
                BreakoutSignal(
                    detected=True,
                    direction="bullish",
                    breakout_level=resistance,
                    candle_index=len(df) - 1,
                    timestamp=str(last["timestamp"]),
                )
            )

    # Check if broke below the lowest recent swing low
    if swing_lows:
        support = min(v for _, v in swing_lows[-3:])
        last = df.iloc[-1]
        if last["close"] < support - threshold:
            signals.append(
                BreakoutSignal(
                    detected=True,
                    direction="bearish",
                    breakout_level=support,
                    candle_index=len(df) - 1,
                    timestamp=str(last["timestamp"]),
                )
            )

    return signals


def detect_pullbacks(
    df: pd.DataFrame, lookback: int = 20
) -> list[PullbackSignal]:
    """Detect pullbacks: temporary retracement against the prevailing trend
    that doesn't violate trend structure.

    Looks for a move against the trend followed by resumption.
    """
    if len(df) < MIN_BARS_TREND:
        return []

    signals: list[PullbackSignal] = []

    # Get the trend from a wider window
    trend = classify_trend(df, lookback=lookback)
    if trend.direction == "ranging":
        return []

    recent = df.iloc[-lookback:]
    swing_highs = find_swing_highs(recent["high"], order=max(2, PIVOT_ORDER - 1))
    swing_lows = find_swing_lows(recent["low"], order=max(2, PIVOT_ORDER - 1))

    if trend.direction == "bullish" and len(swing_highs) >= 2 and len(swing_lows) >= 1:
        # In an uptrend, a pullback is a dip to a swing low after a swing high
        last_high_idx, last_high_val = swing_highs[-1]
        # Find the swing low after the last swing high
        lows_after = [(i, v) for i, v in swing_lows if i > last_high_idx]
        if not lows_after and swing_lows:
            # Use the most recent swing low
            low_idx, low_val = swing_lows[-1]
            # Check the high before this low
            highs_before = [(i, v) for i, v in swing_highs if i < low_idx]
            if highs_before:
                prior_high_val = highs_before[-1][1]
                move = prior_high_val - min(recent["low"])
                if move > 0:
                    depth = (prior_high_val - low_val) / move
                    if PULLBACK_MIN_DEPTH <= depth <= PULLBACK_MAX_DEPTH:
                        # Check if price has resumed upward after the low
                        bars_after_low = recent.iloc[low_idx + 1 :]
                        if len(bars_after_low) > 0 and bars_after_low["close"].iloc[-1] > low_val:
                            actual_idx = len(df) - lookback + low_idx
                            signals.append(
                                PullbackSignal(
                                    detected=True,
                                    direction="bullish",
                                    depth_pct=round(depth * 100, 1),
                                    candle_index=actual_idx,
                                    timestamp=str(recent.iloc[low_idx]["timestamp"]),
                                )
                            )

    elif trend.direction == "bearish" and len(swing_lows) >= 2 and len(swing_highs) >= 1:
        last_low_idx, last_low_val = swing_lows[-1]
        highs_after = [(i, v) for i, v in swing_highs if i > last_low_idx]
        if not highs_after and swing_highs:
            high_idx, high_val = swing_highs[-1]
            lows_before = [(i, v) for i, v in swing_lows if i < high_idx]
            if lows_before:
                prior_low_val = lows_before[-1][1]
                move = max(recent["high"]) - prior_low_val
                if move > 0:
                    depth = (high_val - prior_low_val) / move
                    if PULLBACK_MIN_DEPTH <= depth <= PULLBACK_MAX_DEPTH:
                        bars_after_high = recent.iloc[high_idx + 1 :]
                        if len(bars_after_high) > 0 and bars_after_high["close"].iloc[-1] < high_val:
                            actual_idx = len(df) - lookback + high_idx
                            signals.append(
                                PullbackSignal(
                                    detected=True,
                                    direction="bearish",
                                    depth_pct=round(depth * 100, 1),
                                    candle_index=actual_idx,
                                    timestamp=str(recent.iloc[high_idx]["timestamp"]),
                                )
                            )

    return signals


def detect_range(df: pd.DataFrame, lookback: int = 20) -> RangeState:
    """Detect range/consolidation: price oscillating within a tight band.

    Checks if the high-low range of the last ``lookback`` candles is small
    relative to the midprice.
    """
    if len(df) < RANGE_MIN_BARS:
        return RangeState()

    recent = df.iloc[-lookback:] if len(df) >= lookback else df

    range_high = float(recent["high"].max())
    range_low = float(recent["low"].min())
    mid = (range_high + range_low) / 2
    if mid == 0:
        return RangeState()

    range_pct = (range_high - range_low) / mid

    if range_pct <= RANGE_THRESHOLD_RATIO:
        return RangeState(
            detected=True,
            range_high=range_high,
            range_low=range_low,
            duration_bars=len(recent),
        )

    return RangeState()


def detect_rejections(
    df: pd.DataFrame, lookback: int = 5
) -> list[RejectionSignal]:
    """Detect rejection candles: long-wick candles that rejected a price
    level, suggesting a reversal.

    Scans the last ``lookback`` candles for long wicks relative to body.
    """
    if len(df) < 2:
        return []

    signals: list[RejectionSignal] = []
    start = max(0, len(df) - lookback)

    for i in range(start, len(df)):
        row = df.iloc[i]
        body = abs(row["close"] - row["open"])
        upper_wick = row["high"] - max(row["close"], row["open"])
        lower_wick = min(row["close"], row["open"]) - row["low"]

        if body < 1e-8:
            continue

        # Bullish rejection: long lower wick (rejected from below, bounced up)
        if lower_wick >= REJECTION_WICK_MULTIPLE * body and lower_wick > upper_wick:
            signals.append(
                RejectionSignal(
                    detected=True,
                    level=float(row["low"]),
                    direction="bullish",
                    candle_index=i,
                    timestamp=str(row["timestamp"]),
                )
            )

        # Bearish rejection: long upper wick (rejected from above, pushed down)
        elif upper_wick >= REJECTION_WICK_MULTIPLE * body and upper_wick > lower_wick:
            signals.append(
                RejectionSignal(
                    detected=True,
                    level=float(row["high"]),
                    direction="bearish",
                    candle_index=i,
                    timestamp=str(row["timestamp"]),
                )
            )

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# Top-level assembler
# ═══════════════════════════════════════════════════════════════════════════

def analyze_price_action(
    df: pd.DataFrame, lookback: int = 20
) -> PriceActionResult:
    """Run all price-action detectors on the given OHLC DataFrame and return
    an aggregated ``PriceActionResult``.

    The DataFrame must have columns: open, high, low, close, timestamp.
    Rows should be sorted chronologically (oldest first).
    """
    if df is None or df.empty:
        return PriceActionResult()

    trend = classify_trend(df, lookback=lookback)
    breakouts = detect_breakouts(df, lookback=lookback)
    pullbacks = detect_pullbacks(df, lookback=lookback)
    range_state = detect_range(df, lookback=lookback)
    rejections = detect_rejections(df, lookback=min(lookback, 5))

    return PriceActionResult(
        trend=trend,
        breakouts=breakouts,
        pullbacks=pullbacks,
        range_state=range_state,
        rejections=rejections,
    )
