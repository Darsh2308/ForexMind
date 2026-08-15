from __future__ import annotations

import pandas as pd

from forexmind.agents.price_action.detectors import (
    find_swing_highs,
    find_swing_lows,
    PIVOT_ORDER,
)
from forexmind.agents.smc.schemas import (
    FairValueGap,
    MarketStructureShift,
    OrderBlock,
    LiquidityPool,
    LiquiditySweep,
    DealingRange,
    SMCResult,
)

# ── Configurable parameters ─────────────────────────────────────────────────

LIQUIDITY_TOLERANCE = 0.0005  # 5 pips for EUR/USD
SWEEP_REJECTION_RATIO = 0.5  # Wick must be at least 50% of the candle to count as a strong sweep rejection


def detect_fvgs(df: pd.DataFrame) -> list[FairValueGap]:
    """Detect Fair Value Gaps (3-candle imbalances) and their mitigation status."""
    fvgs = []
    n = len(df)
    
    if n < 3:
        return fvgs

    # Find raw FVGs
    for i in range(2, n):
        c1 = df.iloc[i - 2]
        c3 = df.iloc[i]
        
        # Bullish FVG
        if c1["high"] < c3["low"]:
            fvgs.append(
                FairValueGap(
                    direction="bullish",
                    top=float(c3["low"]),
                    bottom=float(c1["high"]),
                    candle_index=i,
                    timestamp=str(c3["timestamp"])
                )
            )
        # Bearish FVG
        elif c1["low"] > c3["high"]:
            fvgs.append(
                FairValueGap(
                    direction="bearish",
                    top=float(c1["low"]),
                    bottom=float(c3["high"]),
                    candle_index=i,
                    timestamp=str(c3["timestamp"])
                )
            )

    # Check mitigation
    for fvg in fvgs:
        start_idx = fvg.candle_index + 1
        for j in range(start_idx, n):
            c = df.iloc[j]
            if fvg.direction == "bullish":
                if c["low"] <= fvg.bottom:
                    fvg.mitigated = True
                    break
            else:  # bearish
                if c["high"] >= fvg.top:
                    fvg.mitigated = True
                    break

    return fvgs


def detect_liquidity_and_sweeps(
    df: pd.DataFrame
) -> tuple[list[LiquidityPool], list[LiquiditySweep]]:
    """Detect Equal Highs/Lows and wick sweeps into those pools."""
    pools = []
    sweeps = []
    
    if len(df) < PIVOT_ORDER * 2 + 1:
        return pools, sweeps

    swing_highs = find_swing_highs(df["high"], order=PIVOT_ORDER)
    swing_lows = find_swing_lows(df["low"], order=PIVOT_ORDER)

    # Cluster highs
    high_clusters = []
    # swing_highs is a list of (index, value)
    for idx, val in swing_highs:
        added = False
        for cluster in high_clusters:
            if abs(cluster["price"] - val) <= LIQUIDITY_TOLERANCE:
                cluster["points"].append((idx, val))
                # Update average price
                cluster["price"] = sum(v for _, v in cluster["points"]) / len(cluster["points"])
                added = True
                break
        if not added:
            high_clusters.append({"price": val, "points": [(idx, val)]})

    # Cluster lows
    low_clusters = []
    for idx, val in swing_lows:
        added = False
        for cluster in low_clusters:
            if abs(cluster["price"] - val) <= LIQUIDITY_TOLERANCE:
                cluster["points"].append((idx, val))
                cluster["price"] = sum(v for _, v in cluster["points"]) / len(cluster["points"])
                added = True
                break
        if not added:
            low_clusters.append({"price": val, "points": [(idx, val)]})

    for cluster in high_clusters:
        pts = cluster["points"]
        pt_type = "EQH" if len(pts) >= 2 else "swing_high"
        
        # Check if swept (a candle later wicks above but closes below)
        last_idx = max(idx for idx, _ in pts)
        swept = False
        
        for i in range(last_idx + 1, len(df)):
            c = df.iloc[i]
            if c["high"] > cluster["price"] and c["close"] <= cluster["price"]:
                # Check rejection ratio (is it a decent wick?)
                candle_range = c["high"] - c["low"]
                wick_len = c["high"] - max(c["open"], c["close"])
                if candle_range > 0 and (wick_len / candle_range) >= SWEEP_REJECTION_RATIO:
                    swept = True
                    sweeps.append(
                        LiquiditySweep(
                            direction="bearish",
                            pool_type=pt_type,
                            sweep_price=float(c["high"]),
                            candle_index=i,
                            timestamp=str(c["timestamp"])
                        )
                    )
                    break
        
        pools.append(
            LiquidityPool(
                type=pt_type,
                price=float(cluster["price"]),
                touches=len(pts),
                candle_indices=[idx for idx, _ in pts],
                swept=swept
            )
        )

    for cluster in low_clusters:
        pts = cluster["points"]
        pt_type = "EQL" if len(pts) >= 2 else "swing_low"
        
        last_idx = max(idx for idx, _ in pts)
        swept = False
        
        for i in range(last_idx + 1, len(df)):
            c = df.iloc[i]
            if c["low"] < cluster["price"] and c["close"] >= cluster["price"]:
                candle_range = c["high"] - c["low"]
                wick_len = min(c["open"], c["close"]) - c["low"]
                if candle_range > 0 and (wick_len / candle_range) >= SWEEP_REJECTION_RATIO:
                    swept = True
                    sweeps.append(
                        LiquiditySweep(
                            direction="bullish",
                            pool_type=pt_type,
                            sweep_price=float(c["low"]),
                            candle_index=i,
                            timestamp=str(c["timestamp"])
                        )
                    )
                    break
        
        pools.append(
            LiquidityPool(
                type=pt_type,
                price=float(cluster["price"]),
                touches=len(pts),
                candle_indices=[idx for idx, _ in pts],
                swept=swept
            )
        )

    return pools, sweeps


def detect_market_structure_and_obs(
    df: pd.DataFrame
) -> tuple[list[MarketStructureShift], list[OrderBlock]]:
    """Simplified detection of BOS/CHOCH and corresponding Order Blocks."""
    shifts = []
    obs = []
    
    if len(df) < PIVOT_ORDER * 2 + 1:
        return shifts, obs

    swing_highs = find_swing_highs(df["high"], order=PIVOT_ORDER)
    swing_lows = find_swing_lows(df["low"], order=PIVOT_ORDER)
    
    if not swing_highs or not swing_lows:
        return shifts, obs

    # Combine and sort swings by time
    all_swings = []
    for idx, val in swing_highs:
        all_swings.append((idx, val, "high"))
    for idx, val in swing_lows:
        all_swings.append((idx, val, "low"))
        
    all_swings.sort(key=lambda x: x[0])
    
    # Track the state to identify BOS vs CHOCH. 
    # This is a very simplified state machine.
    last_high = None
    last_low = None
    current_trend = None  # "bullish" or "bearish"
    
    for idx, val, s_type in all_swings:
        if s_type == "high":
            if last_high is not None and val > last_high:
                if current_trend in ["bullish", None]:
                    shifts.append(
                        MarketStructureShift(
                            type="BOS", direction="bullish", level=last_high, candle_index=idx, timestamp=str(df.iloc[idx]["timestamp"])
                        )
                    )
                elif current_trend == "bearish":
                    shifts.append(
                        MarketStructureShift(
                            type="CHOCH", direction="bullish", level=last_high, candle_index=idx, timestamp=str(df.iloc[idx]["timestamp"])
                        )
                    )
                current_trend = "bullish"
            last_high = val
            
        else: # s_type == "low"
            if last_low is not None and val < last_low:
                if current_trend in ["bearish", None]:
                    shifts.append(
                        MarketStructureShift(
                            type="BOS", direction="bearish", level=last_low, candle_index=idx, timestamp=str(df.iloc[idx]["timestamp"])
                        )
                    )
                elif current_trend == "bullish":
                    shifts.append(
                        MarketStructureShift(
                            type="CHOCH", direction="bearish", level=last_low, candle_index=idx, timestamp=str(df.iloc[idx]["timestamp"])
                        )
                    )
                current_trend = "bearish"
            last_low = val

    # For each shift, find the order block
    for shift in shifts:
        shift_idx = shift.candle_index
        # Look back from the shift to find the impulse origin
        # Simple OB definition: 
        # Bullish shift -> last down candle before the up move
        # Bearish shift -> last up candle before the down move
        ob = None
        if shift.direction == "bullish":
            for i in range(shift_idx - 1, max(-1, shift_idx - 20), -1):
                c = df.iloc[i]
                if c["close"] < c["open"]: # down candle
                    ob = OrderBlock(
                        direction="bullish",
                        top=float(c["high"]),
                        bottom=float(c["low"]),
                        candle_index=i,
                        timestamp=str(c["timestamp"])
                    )
                    break
        else:
            for i in range(shift_idx - 1, max(-1, shift_idx - 20), -1):
                c = df.iloc[i]
                if c["close"] > c["open"]: # up candle
                    ob = OrderBlock(
                        direction="bearish",
                        top=float(c["high"]),
                        bottom=float(c["low"]),
                        candle_index=i,
                        timestamp=str(c["timestamp"])
                    )
                    break
                    
        if ob:
            # Check mitigation
            start_idx = shift_idx + 1
            for j in range(start_idx, len(df)):
                c = df.iloc[j]
                if ob.direction == "bullish" and c["low"] <= ob.top:
                    ob.mitigated = True
                    break
                elif ob.direction == "bearish" and c["high"] >= ob.bottom:
                    ob.mitigated = True
                    break
            obs.append(ob)

    return shifts, obs


def calculate_dealing_range(df: pd.DataFrame) -> DealingRange | None:
    """Calculate the dealing range using the most recent major swing high and low."""
    if len(df) < PIVOT_ORDER * 2 + 1:
        return None

    # Use a larger pivot order for major swings
    major_order = max(5, PIVOT_ORDER * 2)
    swing_highs = find_swing_highs(df["high"], order=major_order)
    swing_lows = find_swing_lows(df["low"], order=major_order)
    
    if not swing_highs or not swing_lows:
        return None

    last_high_idx, last_high_val = swing_highs[-1]
    last_low_idx, last_low_val = swing_lows[-1]
    
    high = max(last_high_val, last_low_val) # ensuring high > low
    low = min(last_high_val, last_low_val)
    
    if last_high_val < last_low_val:
        # Inverted due to extreme volatility or small window
        pass 
        
    eq = (high + low) / 2
    
    # OTE (Optimal Trade Entry) is typically the 62-79% retracement of the impulse leg
    # If the impulse was up (low was older than high), retracement is down
    if last_low_idx < last_high_idx:
        # Upward impulse
        ote_high = high - (high - low) * 0.618
        ote_low = high - (high - low) * 0.786
    else:
        # Downward impulse
        ote_high = low + (high - low) * 0.786
        ote_low = low + (high - low) * 0.618

    current_price = df.iloc[-1]["close"]
    if current_price > eq:
        zone = "premium"
    elif current_price < eq:
        zone = "discount"
    else:
        zone = "equilibrium"
        
    return DealingRange(
        swing_high=high,
        swing_low=low,
        equilibrium=eq,
        ote_high=max(ote_high, ote_low),
        ote_low=min(ote_high, ote_low),
        current_zone=zone
    )


def analyze_smc(df: pd.DataFrame) -> SMCResult:
    """Run all SMC detectors."""
    if df.empty:
        return SMCResult()

    fvgs = detect_fvgs(df)
    pools, sweeps = detect_liquidity_and_sweeps(df)
    shifts, obs = detect_market_structure_and_obs(df)
    dr = calculate_dealing_range(df)

    return SMCResult(
        fvgs=fvgs,
        structure_shifts=shifts,
        order_blocks=obs,
        liquidity_pools=pools,
        liquidity_sweeps=sweeps,
        dealing_range=dr
    )
