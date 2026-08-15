"""Pure candlestick-pattern detection — no I/O, no state.

Every public ``detect_*`` function takes a pandas DataFrame with OHLC columns
(``open``, ``high``, ``low``, ``close``, ``timestamp``) sorted chronologically
(oldest first) and returns a list of ``CandlestickPattern`` instances found
in the data.

All detection is mathematical — no LLM.  Configurable thresholds are module-
level constants at the top of the file.
"""

from __future__ import annotations

import logging

import pandas as pd

from forexmind.agents.candlestick.schemas import CandlestickPattern

logger = logging.getLogger(__name__)

# ── Configurable thresholds ──────────────────────────────────────────────────
# Body-to-range ratio: body / (high - low).  A "small body" is below this.
SMALL_BODY_RATIO = 0.30
# A doji has an even tighter body.
DOJI_BODY_RATIO = 0.10
# Wick must be at least this multiple of the body to qualify as "long".
LONG_WICK_BODY_MULTIPLE = 2.0
# Marubozu: wicks must be ≤ this fraction of total range.
MARUBOZU_WICK_RATIO = 0.05
# Spinning top: body must be within this fraction of total range, and wicks
# must be roughly balanced (ratio between upper/lower wick ≤ this).
SPINNING_TOP_BODY_RATIO = 0.30
SPINNING_TOP_WICK_BALANCE = 3.0
# Engulfing tolerance: allow body boundaries to be within this absolute
# tolerance for the "engulfs" check (handles floating-point noise).
ENGULF_TOLERANCE = 1e-6
# Tweezer: matching highs/lows within this fraction of ATR (or absolute if
# ATR is unavailable).
TWEEZER_TOLERANCE_ABS = 0.0003  # ~3 pips for EUR/USD
# Minimum candle range to avoid division-by-zero on flat candles.
MIN_RANGE = 1e-8
# How many recent candles to scan for patterns (0 = scan all).
SCAN_WINDOW = 0


def _body(row: pd.Series) -> float:
    return abs(row["close"] - row["open"])


def _range(row: pd.Series) -> float:
    return max(row["high"] - row["low"], MIN_RANGE)


def _upper_wick(row: pd.Series) -> float:
    return row["high"] - max(row["close"], row["open"])


def _lower_wick(row: pd.Series) -> float:
    return min(row["close"], row["open"]) - row["low"]


def _is_bullish(row: pd.Series) -> bool:
    return row["close"] > row["open"]


def _is_bearish(row: pd.Series) -> bool:
    return row["close"] < row["open"]


def _scan_range(df: pd.DataFrame, min_candles: int = 1) -> range:
    """Return the index range to scan.  If SCAN_WINDOW is set, only the last
    N candles are checked; otherwise the full frame minus any lookback
    requirement for multi-candle patterns."""
    n = len(df)
    if n < min_candles:
        return range(0, 0)
    start = max(min_candles - 1, n - SCAN_WINDOW) if SCAN_WINDOW > 0 else min_candles - 1
    return range(start, n)


# ═══════════════════════════════════════════════════════════════════════════
# Single-candle patterns
# ═══════════════════════════════════════════════════════════════════════════

def detect_hammer(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Hammer: small body near the top, long lower wick ≥ 2× body, small
    upper wick.  Bullish reversal signal (context-independent here)."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df):
        row = df.iloc[i]
        body = _body(row)
        rng = _range(row)
        lower = _lower_wick(row)
        upper = _upper_wick(row)
        body_ratio = body / rng

        if (
            body_ratio <= SMALL_BODY_RATIO
            and body > 0
            and lower >= LONG_WICK_BODY_MULTIPLE * body
            and upper <= body + ENGULF_TOLERANCE
        ):
            patterns.append(
                CandlestickPattern(
                    name="hammer",
                    type="single",
                    direction="bullish",
                    candle_index=i,
                    timestamp=str(row["timestamp"]),
                )
            )
    return patterns


def detect_hanging_man(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Hanging Man: identical shape to hammer but bearish signal.
    Same geometry — the contextual distinction (uptrend vs downtrend) is
    left to the Price Action Agent; here we just detect the shape and label
    it as bearish."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df):
        row = df.iloc[i]
        body = _body(row)
        rng = _range(row)
        lower = _lower_wick(row)
        upper = _upper_wick(row)
        body_ratio = body / rng

        if (
            body_ratio <= SMALL_BODY_RATIO
            and body > 0
            and lower >= LONG_WICK_BODY_MULTIPLE * body
            and upper <= body + ENGULF_TOLERANCE
        ):
            # Distinguish from hammer by requiring a prior uptrend (≥2 rising closes)
            if i >= 2:
                prior_closes = [float(df.iloc[k]["close"]) for k in range(max(0, i - 3), i)]
                if len(prior_closes) >= 2 and all(
                    prior_closes[j] > prior_closes[j - 1]
                    for j in range(1, len(prior_closes))
                ):
                    patterns.append(
                        CandlestickPattern(
                            name="hanging_man",
                            type="single",
                            direction="bearish",
                            candle_index=i,
                            timestamp=str(row["timestamp"]),
                        )
                    )
    return patterns


def detect_doji(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Doji: body is ≤ DOJI_BODY_RATIO of the total range.  Neutral
    (indecision) signal."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df):
        row = df.iloc[i]
        rng = _range(row)
        body_ratio = _body(row) / rng

        if body_ratio <= DOJI_BODY_RATIO:
            patterns.append(
                CandlestickPattern(
                    name="doji",
                    type="single",
                    direction="neutral",
                    candle_index=i,
                    timestamp=str(row["timestamp"]),
                )
            )
    return patterns


def detect_shooting_star(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Shooting Star: small body at the bottom, long upper wick ≥ 2× body,
    small lower wick.  Bearish reversal signal."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df):
        row = df.iloc[i]
        body = _body(row)
        rng = _range(row)
        upper = _upper_wick(row)
        lower = _lower_wick(row)
        body_ratio = body / rng

        if (
            body_ratio <= SMALL_BODY_RATIO
            and body > 0
            and upper >= LONG_WICK_BODY_MULTIPLE * body
            and lower <= body + ENGULF_TOLERANCE
        ):
            patterns.append(
                CandlestickPattern(
                    name="shooting_star",
                    type="single",
                    direction="bearish",
                    candle_index=i,
                    timestamp=str(row["timestamp"]),
                )
            )
    return patterns


def detect_marubozu(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Marubozu: full-body candle with negligible wicks.  Direction matches
    the candle color."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df):
        row = df.iloc[i]
        rng = _range(row)
        upper = _upper_wick(row)
        lower = _lower_wick(row)

        if upper / rng <= MARUBOZU_WICK_RATIO and lower / rng <= MARUBOZU_WICK_RATIO:
            direction = "bullish" if _is_bullish(row) else "bearish"
            patterns.append(
                CandlestickPattern(
                    name="marubozu",
                    type="single",
                    direction=direction,
                    candle_index=i,
                    timestamp=str(row["timestamp"]),
                )
            )
    return patterns


def detect_spinning_top(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Spinning Top: small body with upper and lower wicks that are roughly
    balanced.  Neutral (indecision) signal."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df):
        row = df.iloc[i]
        body = _body(row)
        rng = _range(row)
        upper = _upper_wick(row)
        lower = _lower_wick(row)
        body_ratio = body / rng

        if body_ratio <= SPINNING_TOP_BODY_RATIO and body_ratio > DOJI_BODY_RATIO:
            # Both wicks must be present and roughly balanced
            if upper > 0 and lower > 0:
                wick_ratio = max(upper, lower) / min(upper, lower)
                if wick_ratio <= SPINNING_TOP_WICK_BALANCE:
                    patterns.append(
                        CandlestickPattern(
                            name="spinning_top",
                            type="single",
                            direction="neutral",
                            candle_index=i,
                            timestamp=str(row["timestamp"]),
                        )
                    )
    return patterns


# ═══════════════════════════════════════════════════════════════════════════
# Multi-candle patterns
# ═══════════════════════════════════════════════════════════════════════════

def detect_engulfing(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Engulfing: current candle's body completely engulfs the previous
    candle's body, with opposite color."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df, min_candles=2):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        prev_open, prev_close = prev["open"], prev["close"]
        curr_open, curr_close = curr["open"], curr["close"]

        prev_body_hi = max(prev_open, prev_close)
        prev_body_lo = min(prev_open, prev_close)
        curr_body_hi = max(curr_open, curr_close)
        curr_body_lo = min(curr_open, curr_close)

        # Bullish engulfing: prev bearish, curr bullish, curr body engulfs prev body
        if (
            _is_bearish(prev)
            and _is_bullish(curr)
            and curr_body_lo <= prev_body_lo + ENGULF_TOLERANCE
            and curr_body_hi >= prev_body_hi - ENGULF_TOLERANCE
            and _body(curr) > _body(prev)
        ):
            patterns.append(
                CandlestickPattern(
                    name="bullish_engulfing",
                    type="multi",
                    direction="bullish",
                    candle_index=i,
                    timestamp=str(curr["timestamp"]),
                )
            )
        # Bearish engulfing: prev bullish, curr bearish, curr body engulfs prev body
        elif (
            _is_bullish(prev)
            and _is_bearish(curr)
            and curr_body_lo <= prev_body_lo + ENGULF_TOLERANCE
            and curr_body_hi >= prev_body_hi - ENGULF_TOLERANCE
            and _body(curr) > _body(prev)
        ):
            patterns.append(
                CandlestickPattern(
                    name="bearish_engulfing",
                    type="multi",
                    direction="bearish",
                    candle_index=i,
                    timestamp=str(curr["timestamp"]),
                )
            )
    return patterns


def detect_harami(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Harami: current candle's body is contained within the previous candle's
    body, opposite color."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df, min_candles=2):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        prev_body_hi = max(prev["open"], prev["close"])
        prev_body_lo = min(prev["open"], prev["close"])
        curr_body_hi = max(curr["open"], curr["close"])
        curr_body_lo = min(curr["open"], curr["close"])

        # Current body must be inside previous body
        inside = (
            curr_body_hi <= prev_body_hi + ENGULF_TOLERANCE
            and curr_body_lo >= prev_body_lo - ENGULF_TOLERANCE
            and _body(curr) < _body(prev)
        )
        if not inside:
            continue

        if _is_bearish(prev) and _is_bullish(curr):
            patterns.append(
                CandlestickPattern(
                    name="bullish_harami",
                    type="multi",
                    direction="bullish",
                    candle_index=i,
                    timestamp=str(curr["timestamp"]),
                )
            )
        elif _is_bullish(prev) and _is_bearish(curr):
            patterns.append(
                CandlestickPattern(
                    name="bearish_harami",
                    type="multi",
                    direction="bearish",
                    candle_index=i,
                    timestamp=str(curr["timestamp"]),
                )
            )
    return patterns


def detect_morning_star(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Morning Star (3-candle bullish reversal):
    1. Large bearish candle
    2. Small-body candle (gap down or small real body)
    3. Large bullish candle that closes above the midpoint of candle 1's body
    """
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df, min_candles=3):
        c1 = df.iloc[i - 2]
        c2 = df.iloc[i - 1]
        c3 = df.iloc[i]

        c1_body = _body(c1)
        c2_body = _body(c2)
        c3_body = _body(c3)
        c1_range = _range(c1)

        c1_midpoint = (c1["open"] + c1["close"]) / 2

        if (
            _is_bearish(c1)
            and c1_body / c1_range > SMALL_BODY_RATIO  # c1 is a large candle
            and c2_body / _range(c2) <= SMALL_BODY_RATIO  # c2 is small-bodied
            and _is_bullish(c3)
            and c3_body > c2_body  # c3 is larger than c2
            and c3["close"] > c1_midpoint  # c3 closes above c1 midpoint
        ):
            patterns.append(
                CandlestickPattern(
                    name="morning_star",
                    type="multi",
                    direction="bullish",
                    candle_index=i,
                    timestamp=str(c3["timestamp"]),
                )
            )
    return patterns


def detect_evening_star(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Evening Star (3-candle bearish reversal):
    1. Large bullish candle
    2. Small-body candle
    3. Large bearish candle that closes below the midpoint of candle 1's body
    """
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df, min_candles=3):
        c1 = df.iloc[i - 2]
        c2 = df.iloc[i - 1]
        c3 = df.iloc[i]

        c1_body = _body(c1)
        c2_body = _body(c2)
        c3_body = _body(c3)
        c1_range = _range(c1)

        c1_midpoint = (c1["open"] + c1["close"]) / 2

        if (
            _is_bullish(c1)
            and c1_body / c1_range > SMALL_BODY_RATIO
            and c2_body / _range(c2) <= SMALL_BODY_RATIO
            and _is_bearish(c3)
            and c3_body > c2_body
            and c3["close"] < c1_midpoint
        ):
            patterns.append(
                CandlestickPattern(
                    name="evening_star",
                    type="multi",
                    direction="bearish",
                    candle_index=i,
                    timestamp=str(c3["timestamp"]),
                )
            )
    return patterns


def detect_three_white_soldiers(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Three White Soldiers: 3 consecutive bullish candles, each opening
    within the previous body and closing higher."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df, min_candles=3):
        c1 = df.iloc[i - 2]
        c2 = df.iloc[i - 1]
        c3 = df.iloc[i]

        if not (_is_bullish(c1) and _is_bullish(c2) and _is_bullish(c3)):
            continue

        # Each candle should have a meaningful body (not doji)
        if any(
            _body(c) / _range(c) <= DOJI_BODY_RATIO for c in [c1, c2, c3]
        ):
            continue

        # Each opens within the previous candle's body
        if not (
            c1["open"] <= c2["open"] <= c1["close"]
            and c2["open"] <= c3["open"] <= c2["close"]
        ):
            continue

        # Each closes higher than the previous
        if c3["close"] > c2["close"] > c1["close"]:
            patterns.append(
                CandlestickPattern(
                    name="three_white_soldiers",
                    type="multi",
                    direction="bullish",
                    candle_index=i,
                    timestamp=str(c3["timestamp"]),
                )
            )
    return patterns


def detect_three_black_crows(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Three Black Crows: 3 consecutive bearish candles, each opening
    within the previous body and closing lower."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df, min_candles=3):
        c1 = df.iloc[i - 2]
        c2 = df.iloc[i - 1]
        c3 = df.iloc[i]

        if not (_is_bearish(c1) and _is_bearish(c2) and _is_bearish(c3)):
            continue

        if any(
            _body(c) / _range(c) <= DOJI_BODY_RATIO for c in [c1, c2, c3]
        ):
            continue

        # Each opens within the previous candle's body (for bearish: close < open)
        if not (
            c1["close"] <= c2["open"] <= c1["open"]
            and c2["close"] <= c3["open"] <= c2["open"]
        ):
            continue

        # Each closes lower
        if c3["close"] < c2["close"] < c1["close"]:
            patterns.append(
                CandlestickPattern(
                    name="three_black_crows",
                    type="multi",
                    direction="bearish",
                    candle_index=i,
                    timestamp=str(c3["timestamp"]),
                )
            )
    return patterns


def detect_tweezer_top(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Tweezer Top: two consecutive candles with matching highs at a potential
    top (first bullish, second bearish)."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df, min_candles=2):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        if (
            _is_bullish(prev)
            and _is_bearish(curr)
            and abs(prev["high"] - curr["high"]) <= TWEEZER_TOLERANCE_ABS
        ):
            patterns.append(
                CandlestickPattern(
                    name="tweezer_top",
                    type="multi",
                    direction="bearish",
                    candle_index=i,
                    timestamp=str(curr["timestamp"]),
                )
            )
    return patterns


def detect_tweezer_bottom(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Tweezer Bottom: two consecutive candles with matching lows at a
    potential bottom (first bearish, second bullish)."""
    patterns: list[CandlestickPattern] = []
    for i in _scan_range(df, min_candles=2):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        if (
            _is_bearish(prev)
            and _is_bullish(curr)
            and abs(prev["low"] - curr["low"]) <= TWEEZER_TOLERANCE_ABS
        ):
            patterns.append(
                CandlestickPattern(
                    name="tweezer_bottom",
                    type="multi",
                    direction="bullish",
                    candle_index=i,
                    timestamp=str(curr["timestamp"]),
                )
            )
    return patterns


# ═══════════════════════════════════════════════════════════════════════════
# Top-level runner
# ═══════════════════════════════════════════════════════════════════════════

ALL_DETECTORS = [
    # Single-candle
    detect_hammer,
    detect_hanging_man,
    detect_doji,
    detect_shooting_star,
    detect_marubozu,
    detect_spinning_top,
    # Multi-candle
    detect_engulfing,
    detect_harami,
    detect_morning_star,
    detect_evening_star,
    detect_three_white_soldiers,
    detect_three_black_crows,
    detect_tweezer_top,
    detect_tweezer_bottom,
]


def detect_all_patterns(df: pd.DataFrame) -> list[CandlestickPattern]:
    """Run every pattern detector on the given OHLC DataFrame and return
    all detected patterns, sorted by candle_index."""
    if df is None or df.empty:
        return []
    all_patterns: list[CandlestickPattern] = []
    for detector in ALL_DETECTORS:
        try:
            all_patterns.extend(detector(df))
        except Exception:
            logger.exception("Pattern detector %s failed", detector.__name__)
    all_patterns.sort(key=lambda p: p.candle_index)
    return all_patterns
