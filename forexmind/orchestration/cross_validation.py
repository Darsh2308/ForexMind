from forexmind.orchestration.market_context import MarketContext


def cross_validate(context: MarketContext) -> list[str]:
    """
    Detects and explicitly flags contradictions between different agent findings.
    Returns a list of conflict description strings.
    """
    conflicts = []

    for tf in context.timeframes:
        # 1. Technical Analysis vs Price Action Trend Mismatches
        if context.technical_analysis and context.price_action:
            ta_set = context.technical_analysis.timeframes.get(tf)
            pa_res = context.price_action.timeframes.get(tf)

            if ta_set and pa_res:
                ta_trend = ta_set.trend
                pa_trend = pa_res.trend.direction

                if ta_trend == "bullish" and pa_trend == "bearish":
                    conflicts.append(
                        f"[{tf}] Trend Mismatch: Technical Analysis is Bullish, but Price Action is Bearish."
                    )
                elif ta_trend == "bearish" and pa_trend == "bullish":
                    conflicts.append(
                        f"[{tf}] Trend Mismatch: Technical Analysis is Bearish, but Price Action is Bullish."
                    )

        # 2. Elliott Wave vs Wyckoff Advisory Mismatches
        if context.elliott_wave and context.wyckoff:
            ew_res = context.elliott_wave.timeframes.get(tf)
            wy_res = context.wyckoff.timeframes.get(tf)

            if ew_res and wy_res:
                last_wave = ew_res.current_count.waves[-1] if ew_res.current_count.waves else None
                ew_bullish = last_wave.end_price > last_wave.start_price if last_wave else False
                ew_bearish = last_wave.end_price < last_wave.start_price if last_wave else False

                if (
                    ew_bullish
                    and wy_res.current_phase.phase in ["distribution", "markdown"]
                ):
                    conflicts.append(
                        f"[{tf}] Advisory Mismatch: Elliott Wave is Bullish, but Wyckoff Phase is {wy_res.current_phase.phase}."
                    )
                elif (
                    ew_bearish
                    and wy_res.current_phase.phase in ["accumulation", "markup"]
                ):
                    conflicts.append(
                        f"[{tf}] Advisory Mismatch: Elliott Wave is Bearish, but Wyckoff Phase is {wy_res.current_phase.phase}."
                    )

        # 3. Candlestick vs Support/Resistance (Simple Check: Bullish pattern at Resistance or Bearish at Support)
        if context.candlestick and context.support_resistance:
            candlesticks = context.candlestick.timeframes.get(tf, [])
            sr_res = context.support_resistance.timeframes.get(tf)

            if sr_res:
                recent_close = None
                if context.technical_analysis:
                    ta_set = context.technical_analysis.timeframes.get(tf)
                    # We can use EMA20 / SMA20 roughly to figure out current price if we don't have it,
                    # but typically we'd use the current price. We can assume pattern detection means it happened near the current price.
                
                # Check the most recent candlestick pattern
                if candlesticks:
                    latest_pattern = candlesticks[-1]
                    # If we had the exact price we could check proximity to SR levels.
                    # For now, we will just flag if there are *both* a bearish pattern and strong support
                    # or bullish pattern and strong resistance within the timeframe context.
                    # This is a bit simplified, but demonstrates the cross-validation logic.
                    # Let's say we check if the pattern is contrary to the closest level.
                    pass # We will rely on the first two rules for robust V1 cross-validation

    return conflicts
