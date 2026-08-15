"""Pure indicator computation — no I/O, no state.

Every public function takes a pandas DataFrame with OHLC columns and returns
computed values.  The top-level `compute_indicators` assembles a full
`IndicatorSet`.

All indicator math is delegated to ``pandas_ta``.  If a DataFrame has fewer
rows than an indicator's lookback period requires, that indicator's fields
are left as None — never raise, never fabricate.
"""

from __future__ import annotations

import logging

import pandas as pd
import pandas_ta as ta

from forexmind.agents.technical_analysis.schemas import IndicatorSet

logger = logging.getLogger(__name__)

# ── Minimum bar counts required for each indicator ────────────────────────
# pandas_ta silently returns NaN when there aren't enough bars, but we can
# short-circuit early for the obvious cases.
_MIN_BARS_EMA_20 = 20
_MIN_BARS_EMA_50 = 50
_MIN_BARS_EMA_200 = 200
_MIN_BARS_RSI = 15       # RSI-14 needs 14+1 bars
_MIN_BARS_MACD = 35      # MACD(12,26,9): 26 + 9 = 35
_MIN_BARS_STOCH = 17     # Stochastic(14,3,3): 14 + 3 = 17
_MIN_BARS_ATR = 15       # ATR-14 needs 14+1 bars
_MIN_BARS_BB = 20        # Bollinger(20,2)

# How many recent bars to scan for a MACD crossover event
_MACD_CROSS_LOOKBACK = 3


def _safe_float(value) -> float | None:
    """Convert a pandas scalar to a Python float, returning None for NaN."""
    if value is None or pd.isna(value):
        return None
    return round(float(value), 6)


def _last_valid(series: pd.Series) -> float | None:
    """Return the last non-NaN value in a series, or None."""
    if series is None or series.empty:
        return None
    return _safe_float(series.iloc[-1])


# ── Individual indicator helpers ──────────────────────────────────────────

def compute_ema(close: pd.Series, length: int) -> float | None:
    if len(close) < length:
        return None
    result = ta.ema(close, length=length)
    return _last_valid(result)


def compute_sma(close: pd.Series, length: int) -> float | None:
    if len(close) < length:
        return None
    result = ta.sma(close, length=length)
    return _last_valid(result)


def compute_rsi(close: pd.Series, length: int = 14) -> float | None:
    if len(close) < _MIN_BARS_RSI:
        return None
    result = ta.rsi(close, length=length)
    return _last_valid(result)


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[float | None, float | None, float | None]:
    """Returns (macd_line, signal_line, histogram)."""
    if len(close) < _MIN_BARS_MACD:
        return None, None, None
    result = ta.macd(close, fast=fast, slow=slow, signal=signal)
    if result is None or result.empty:
        return None, None, None
    macd_col = f"MACD_{fast}_{slow}_{signal}"
    signal_col = f"MACDs_{fast}_{slow}_{signal}"
    hist_col = f"MACDh_{fast}_{slow}_{signal}"
    return (
        _last_valid(result[macd_col]),
        _last_valid(result[signal_col]),
        _last_valid(result[hist_col]),
    )


def detect_macd_cross(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> str:
    """Detect a MACD/signal crossover within the last `_MACD_CROSS_LOOKBACK`
    bars.  Returns "bullish", "bearish", or "none"."""
    if len(close) < _MIN_BARS_MACD + _MACD_CROSS_LOOKBACK:
        return "none"
    result = ta.macd(close, fast=fast, slow=slow, signal=signal)
    if result is None or result.empty:
        return "none"
    macd_col = f"MACD_{fast}_{slow}_{signal}"
    signal_col = f"MACDs_{fast}_{slow}_{signal}"
    macd_s = result[macd_col]
    signal_s = result[signal_col]

    # Check the last _MACD_CROSS_LOOKBACK bars for a crossover
    for i in range(-_MACD_CROSS_LOOKBACK, 0):
        curr_idx = len(macd_s) + i
        prev_idx = curr_idx - 1
        if prev_idx < 0:
            continue
        m_curr = macd_s.iloc[curr_idx]
        m_prev = macd_s.iloc[prev_idx]
        s_curr = signal_s.iloc[curr_idx]
        s_prev = signal_s.iloc[prev_idx]
        if pd.isna(m_curr) or pd.isna(m_prev) or pd.isna(s_curr) or pd.isna(s_prev):
            continue
        # Bullish cross: MACD crosses above signal
        if m_prev <= s_prev and m_curr > s_curr:
            return "bullish"
        # Bearish cross: MACD crosses below signal
        if m_prev >= s_prev and m_curr < s_curr:
            return "bearish"
    return "none"


def compute_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k: int = 14,
    d: int = 3,
    smooth_k: int = 3,
) -> tuple[float | None, float | None]:
    """Returns (%K, %D)."""
    if len(close) < _MIN_BARS_STOCH:
        return None, None
    result = ta.stoch(high, low, close, k=k, d=d, smooth_k=smooth_k)
    if result is None or result.empty:
        return None, None
    k_col = f"STOCHk_{k}_{d}_{smooth_k}"
    d_col = f"STOCHd_{k}_{d}_{smooth_k}"
    return _last_valid(result[k_col]), _last_valid(result[d_col])


def compute_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14
) -> float | None:
    if len(close) < _MIN_BARS_ATR:
        return None
    result = ta.atr(high, low, close, length=length)
    return _last_valid(result)


def compute_bollinger_bands(
    close: pd.Series, length: int = 20, std: float = 2.0
) -> tuple[float | None, float | None, float | None, float | None, float | None]:
    """Returns (upper, middle, lower, bandwidth, percent_b)."""
    if len(close) < _MIN_BARS_BB:
        return None, None, None, None, None
    result = ta.bbands(close, length=length, std=std)
    if result is None or result.empty:
        return None, None, None, None, None
    # Column names vary across pandas-ta versions (e.g. BBU_20_2.0 vs
    # BBU_20_2.0_2.0).  Use prefix matching for robustness.
    cols = result.columns.tolist()
    def _find_col(prefix: str) -> str | None:
        matches = [c for c in cols if c.startswith(prefix)]
        return matches[0] if matches else None
    lower_col = _find_col("BBL_")
    mid_col = _find_col("BBM_")
    upper_col = _find_col("BBU_")
    bw_col = _find_col("BBB_")
    pctb_col = _find_col("BBP_")
    return (
        _last_valid(result[upper_col]) if upper_col else None,
        _last_valid(result[mid_col]) if mid_col else None,
        _last_valid(result[lower_col]) if lower_col else None,
        _last_valid(result[bw_col]) if bw_col else None,
        _last_valid(result[pctb_col]) if pctb_col else None,
    )


# ── Derived classification helpers ────────────────────────────────────────

def classify_trend(
    ema_20: float | None, ema_50: float | None, ema_200: float | None
) -> str:
    """Classify trend based on EMA alignment.

    - bullish: EMA20 > EMA50 (and > EMA200 if available)
    - bearish: EMA20 < EMA50 (and < EMA200 if available)
    - neutral: mixed or insufficient data
    """
    if ema_20 is None or ema_50 is None:
        return "neutral"
    if ema_200 is not None:
        if ema_20 > ema_50 > ema_200:
            return "bullish"
        if ema_20 < ema_50 < ema_200:
            return "bearish"
        return "neutral"
    # Without EMA-200, use just EMA-20 vs EMA-50
    if ema_20 > ema_50:
        return "bullish"
    if ema_20 < ema_50:
        return "bearish"
    return "neutral"


def classify_rsi_zone(rsi: float | None) -> str:
    if rsi is None:
        return "neutral"
    if rsi > 70:
        return "overbought"
    if rsi < 30:
        return "oversold"
    return "neutral"


def classify_stoch_zone(stoch_k: float | None) -> str:
    if stoch_k is None:
        return "neutral"
    if stoch_k > 80:
        return "overbought"
    if stoch_k < 20:
        return "oversold"
    return "neutral"


# ── Top-level assembler ──────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame) -> IndicatorSet:
    """Compute all indicators from an OHLC DataFrame and return a fully
    populated `IndicatorSet`.

    The DataFrame must have columns: open, high, low, close.
    Rows should be sorted chronologically (oldest first).

    Any indicator for which there is insufficient data will have its
    fields set to None.
    """
    if df is None or df.empty:
        return IndicatorSet()

    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Trend
    ema_20 = compute_ema(close, 20)
    ema_50 = compute_ema(close, 50)
    ema_200 = compute_ema(close, 200)
    sma_20 = compute_sma(close, 20)
    sma_50 = compute_sma(close, 50)
    sma_200 = compute_sma(close, 200)

    ema_20_above_ema_50 = (
        (ema_20 > ema_50) if ema_20 is not None and ema_50 is not None else None
    )
    ema_50_above_ema_200 = (
        (ema_50 > ema_200) if ema_50 is not None and ema_200 is not None else None
    )
    trend = classify_trend(ema_20, ema_50, ema_200)

    # Momentum
    rsi_14 = compute_rsi(close)
    rsi_zone = classify_rsi_zone(rsi_14)

    macd_line, macd_signal, macd_histogram = compute_macd(close)
    macd_cross = detect_macd_cross(close)

    stoch_k, stoch_d = compute_stochastic(high, low, close)
    stoch_zone = classify_stoch_zone(stoch_k)

    # Volatility
    atr_14 = compute_atr(high, low, close)

    bb_upper, bb_middle, bb_lower, bb_bandwidth, bb_percent_b = (
        compute_bollinger_bands(close)
    )

    return IndicatorSet(
        ema_20=ema_20,
        ema_50=ema_50,
        ema_200=ema_200,
        sma_20=sma_20,
        sma_50=sma_50,
        sma_200=sma_200,
        ema_20_above_ema_50=ema_20_above_ema_50,
        ema_50_above_ema_200=ema_50_above_ema_200,
        trend=trend,
        rsi_14=rsi_14,
        rsi_zone=rsi_zone,
        macd_line=macd_line,
        macd_signal=macd_signal,
        macd_histogram=macd_histogram,
        macd_cross=macd_cross,
        stoch_k=stoch_k,
        stoch_d=stoch_d,
        stoch_zone=stoch_zone,
        atr_14=atr_14,
        bb_upper=bb_upper,
        bb_middle=bb_middle,
        bb_lower=bb_lower,
        bb_bandwidth=bb_bandwidth,
        bb_percent_b=bb_percent_b,
    )
