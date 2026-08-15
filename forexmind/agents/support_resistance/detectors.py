from __future__ import annotations

import pandas as pd
import pandas_ta as ta

from forexmind.agents.price_action.detectors import (
    find_swing_highs,
    find_swing_lows,
    PIVOT_ORDER,
)
from forexmind.agents.support_resistance.schemas import (
    PriceLevel,
    SupportResistanceResult,
)


# ── Configurable parameters ─────────────────────────────────────────────────

# Tolerance for clustering swing points into a single horizontal zone (in absolute price)
# For EUR/USD, 0.0010 = 10 pips. Adjust if pairs have different volatilities.
CLUSTER_TOLERANCE = 0.0010

# Minimum touches for a horizontal level to be considered "strong"
STRONG_TOUCH_THRESHOLD = 3

# Minimum touches for a level to be considered "moderate"
MODERATE_TOUCH_THRESHOLD = 2

# Psychological level interval (e.g. 1.1000, 1.1050)
PSYCHOLOGICAL_INTERVAL = 0.0050

# How close price needs to be to a psychological level to consider it a "level in play"
PSYCHOLOGICAL_PROXIMITY = 0.0020  # 20 pips

# Dynamic EMAs to track
DYNAMIC_EMAS = [50, 200]


def _cluster_points(points: list[float], tolerance: float) -> list[dict]:
    """Cluster 1D points. Returns list of clusters with 'price', 'touches',
    'high', and 'low'."""
    if not points:
        return []

    # Sort points descending
    points = sorted(points, reverse=True)
    clusters = []

    current_cluster = [points[0]]

    for p in points[1:]:
        # If the point is within tolerance of the lowest point in the current cluster
        if current_cluster[-1] - p <= tolerance:
            current_cluster.append(p)
        else:
            clusters.append({
                "price": sum(current_cluster) / len(current_cluster),
                "touches": len(current_cluster),
                "high": max(current_cluster),
                "low": min(current_cluster),
            })
            current_cluster = [p]

    clusters.append({
        "price": sum(current_cluster) / len(current_cluster),
        "touches": len(current_cluster),
        "high": max(current_cluster),
        "low": min(current_cluster),
    })

    return clusters


def detect_horizontal_levels(
    df: pd.DataFrame, current_price: float, lookback: int = 100
) -> tuple[list[PriceLevel], list[PriceLevel]]:
    """Detect horizontal S/R based on clustered swing points over a lookback."""
    if len(df) < lookback:
        window = df
    else:
        window = df.iloc[-lookback:]

    swing_highs = find_swing_highs(window["high"], order=PIVOT_ORDER)
    swing_lows = find_swing_lows(window["low"], order=PIVOT_ORDER)

    high_values = [v for _, v in swing_highs]
    low_values = [v for _, v in swing_lows]

    res_clusters = _cluster_points(high_values, CLUSTER_TOLERANCE)
    sup_clusters = _cluster_points(low_values, CLUSTER_TOLERANCE)

    resistances = []
    for c in res_clusters:
        # A resistance level should ideally be above the current price,
        # but old support becomes new resistance. We just classify based on
        # relation to current price.
        if c["price"] > current_price:
            strength = "strong" if c["touches"] >= STRONG_TOUCH_THRESHOLD else ("moderate" if c["touches"] >= MODERATE_TOUCH_THRESHOLD else "weak")
            resistances.append(
                PriceLevel(
                    price=c["price"],
                    type="horizontal",
                    strength=strength,
                    touch_count=c["touches"],
                    zone_high=c["high"],
                    zone_low=c["low"],
                )
            )

    supports = []
    for c in sup_clusters:
        if c["price"] <= current_price:
            strength = "strong" if c["touches"] >= STRONG_TOUCH_THRESHOLD else ("moderate" if c["touches"] >= MODERATE_TOUCH_THRESHOLD else "weak")
            supports.append(
                PriceLevel(
                    price=c["price"],
                    type="horizontal",
                    strength=strength,
                    touch_count=c["touches"],
                    zone_high=c["high"],
                    zone_low=c["low"],
                )
            )

    return supports, resistances


def detect_psychological_levels(
    current_price: float, interval: float = PSYCHOLOGICAL_INTERVAL, proximity: float = PSYCHOLOGICAL_PROXIMITY
) -> tuple[list[PriceLevel], list[PriceLevel]]:
    """Find round numbers near the current price."""
    supports = []
    resistances = []

    # Find the nearest psychological level below and above
    lower_level = (current_price // interval) * interval
    upper_level = lower_level + interval

    # If current price is extremely close to the lower level, it might act as either
    if current_price - lower_level <= proximity:
        supports.append(
            PriceLevel(
                price=lower_level,
                type="psychological",
                strength="moderate",  # Psych levels are generally moderate unless confluence exists
                touch_count=1,
            )
        )
    else:
        # Keep it as a potential deeper support
        supports.append(
            PriceLevel(
                price=lower_level,
                type="psychological",
                strength="weak",
                touch_count=1,
            )
        )

    if upper_level - current_price <= proximity:
        resistances.append(
            PriceLevel(
                price=upper_level,
                type="psychological",
                strength="moderate",
                touch_count=1,
            )
        )
    else:
        resistances.append(
            PriceLevel(
                price=upper_level,
                type="psychological",
                strength="weak",
                touch_count=1,
            )
        )

    return supports, resistances


def detect_dynamic_levels(
    df: pd.DataFrame, current_price: float
) -> tuple[list[PriceLevel], list[PriceLevel]]:
    """Calculate moving averages that act as dynamic S/R."""
    supports = []
    resistances = []

    for length in DYNAMIC_EMAS:
        if len(df) < length:
            continue
        ema = ta.ema(df["close"], length=length)
        if ema is not None and not pd.isna(ema.iloc[-1]):
            val = float(ema.iloc[-1])
            # A dynamic level below price acts as support; above acts as resistance
            if val <= current_price:
                supports.append(
                    PriceLevel(
                        price=val,
                        type="dynamic",
                        strength="moderate" if length >= 200 else "weak",
                        touch_count=1,
                        source=f"EMA_{length}",
                    )
                )
            else:
                resistances.append(
                    PriceLevel(
                        price=val,
                        type="dynamic",
                        strength="moderate" if length >= 200 else "weak",
                        touch_count=1,
                        source=f"EMA_{length}",
                    )
                )

    return supports, resistances


def analyze_support_resistance(df: pd.DataFrame) -> SupportResistanceResult:
    """Run all S/R detectors and return a unified result."""
    if df.empty:
        return SupportResistanceResult()

    current_price = float(df["close"].iloc[-1])

    h_sup, h_res = detect_horizontal_levels(df, current_price)
    p_sup, p_res = detect_psychological_levels(current_price)
    d_sup, d_res = detect_dynamic_levels(df, current_price)

    supports = h_sup + p_sup + d_sup
    resistances = h_res + p_res + d_res

    # Sort supports descending (closest to current price first)
    supports.sort(key=lambda x: x.price, reverse=True)
    # Sort resistances ascending (closest to current price first)
    resistances.sort(key=lambda x: x.price)

    return SupportResistanceResult(
        support_levels=supports,
        resistance_levels=resistances,
    )
