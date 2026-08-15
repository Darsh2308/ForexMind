from __future__ import annotations

import pandas as pd

from forexmind.agents.price_action.detectors import (
    find_swing_highs,
    find_swing_lows,
    PIVOT_ORDER,
)
from forexmind.agents.wyckoff.schemas import (
    SpringUpthrustEvent,
    WyckoffPhase,
    WyckoffResult,
)


def _detect_phase(df: pd.DataFrame) -> WyckoffPhase:
    """Heuristic for Wyckoff phase based on price location relative to 
    recent highs and lows."""
    if len(df) < 50:
        return WyckoffPhase()

    # Look at the last 50 candles to determine range
    window = df.iloc[-50:]
    recent_high = window["high"].max()
    recent_low = window["low"].min()
    current_price = window["close"].iloc[-1]

    # Calculate relative position (0.0 = at low, 1.0 = at high)
    range_size = recent_high - recent_low
    if range_size == 0:
        return WyckoffPhase()
    
    position = (current_price - recent_low) / range_size

    # Simple heuristic for V1:
    # If it's been ranging (price Action Agent would detect this better, 
    # but we approximate here) and currently testing lows: potential accumulation.
    # Testing highs: potential distribution.
    
    # We will compute a simple trend of the prior 100 candles to see if we 
    # came from a markdown (supports accumulation) or markup (supports distribution).
    if len(df) >= 150:
        prior_window = df.iloc[-150:-50]
        prior_trend = prior_window["close"].iloc[-1] - prior_window["close"].iloc[0]
    else:
        prior_trend = 0

    if position < 0.3 and prior_trend < 0:
        return WyckoffPhase(
            phase="accumulation",
            confidence=0.6,
            support_level=recent_low,
            resistance_level=recent_high,
        )
    elif position > 0.7 and prior_trend > 0:
        return WyckoffPhase(
            phase="distribution",
            confidence=0.6,
            support_level=recent_low,
            resistance_level=recent_high,
        )
    elif prior_trend > 0:
        return WyckoffPhase(
            phase="markup",
            confidence=0.7,
        )
    elif prior_trend < 0:
        return WyckoffPhase(
            phase="markdown",
            confidence=0.7,
        )
        
    return WyckoffPhase()


def _detect_events(df: pd.DataFrame, phase: WyckoffPhase) -> list[SpringUpthrustEvent]:
    """Detect springs (false breakdown) or upthrusts (false breakout)."""
    if len(df) < 10 or phase.phase == "unknown" or phase.support_level is None or phase.resistance_level is None:
        return []

    events = []
    
    # Check the last 10 candles for a sweep of the support/resistance level
    # that closes back inside the range.
    window = df.iloc[-10:]
    
    for idx, row in window.iterrows():
        if phase.phase == "accumulation":
            # Look for a spring: Low is below support, close is above support
            if row["low"] < phase.support_level and row["close"] > phase.support_level:
                events.append(
                    SpringUpthrustEvent(
                        event_type="spring",
                        price_level=row["low"],
                        candle_index=int(idx),
                    )
                )
        elif phase.phase == "distribution":
            # Look for an upthrust: High is above resistance, close is below resistance
            if row["high"] > phase.resistance_level and row["close"] < phase.resistance_level:
                events.append(
                    SpringUpthrustEvent(
                        event_type="upthrust",
                        price_level=row["high"],
                        candle_index=int(idx),
                    )
                )

    return events


def analyze_wyckoff(df: pd.DataFrame) -> WyckoffResult:
    """Analyze price data to detect Wyckoff phases and events."""
    if df.empty:
        return WyckoffResult()
        
    phase = _detect_phase(df)
    events = _detect_events(df, phase)
    
    return WyckoffResult(current_phase=phase, events=events)
