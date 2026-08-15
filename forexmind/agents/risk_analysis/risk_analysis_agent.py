from datetime import datetime, timezone
from forexmind.orchestration.market_context import MarketContext
from forexmind.agents.risk_analysis.schemas import RiskAnalysisSnapshot, TradeSetup

class RiskAnalysisAgent:
    """Agent that calculates dynamic SL/TP and evaluates structure-based R:R."""

    def __init__(self):
        self.atr_buffer_mult = 0.5
        self.min_atr_sl_mult = 0.5
        self.max_atr_sl_mult = 3.0
        self.min_rr = 1.0

    def analyze(self, context: MarketContext) -> RiskAnalysisSnapshot:
        # Extract current price
        md = context.market_data
        if not md:
            return RiskAnalysisSnapshot(as_of=datetime.now(timezone.utc).isoformat())

        current_price = md.latest_price
        if current_price is None and md.timeframes:
            # Fallback to the most recent closed candle
            first_tf = list(md.timeframes.values())[0]
            current_price = first_tf.close

        if current_price is None:
            return RiskAnalysisSnapshot(as_of=datetime.now(timezone.utc).isoformat())

        # Extract ATR
        atr = 0.0010 # fallback default 10 pips
        ta = context.technical_analysis
        if ta and ta.timeframes:
            first_ta_tf = list(ta.timeframes.values())[0]
            if first_ta_tf.atr_14:
                atr = first_ta_tf.atr_14

        # Extract levels
        supports = []
        resistances = []
        
        sr = context.support_resistance
        if sr and sr.timeframes:
            first_sr_tf = list(sr.timeframes.values())[0]
            for lvl in first_sr_tf.support_levels:
                supports.append(lvl.price)
            for lvl in first_sr_tf.resistance_levels:
                resistances.append(lvl.price)

        smc = context.smc
        if smc and smc.timeframes:
            first_smc_tf = list(smc.timeframes.values())[0]
            for ob in first_smc_tf.order_blocks:
                if ob.direction == "bullish":
                    supports.append((ob.top + ob.bottom) / 2.0)
                elif ob.direction == "bearish":
                    resistances.append((ob.top + ob.bottom) / 2.0)

        # Build BUY setup
        buy_setup = self._build_setup(
            direction="BUY",
            entry=current_price,
            atr=atr,
            structural_stops=[s for s in supports if s < current_price],
            structural_targets=[r for r in resistances if r > current_price]
        )

        # Build SELL setup
        sell_setup = self._build_setup(
            direction="SELL",
            entry=current_price,
            atr=atr,
            structural_stops=[r for r in resistances if r > current_price],
            structural_targets=[s for s in supports if s < current_price]
        )

        return RiskAnalysisSnapshot(
            as_of=datetime.now(timezone.utc).isoformat(),
            buy_setup=buy_setup,
            sell_setup=sell_setup,
            volatility_flag=None # Could evaluate if ATR is abnormal
        )

    def _build_setup(
        self, 
        direction: str, 
        entry: float, 
        atr: float, 
        structural_stops: list[float], 
        structural_targets: list[float]
    ) -> TradeSetup | None:
        if not structural_stops or not structural_targets:
            return None
            
        if direction == "BUY":
            # Highest support below entry
            structural_sl = max(structural_stops)
            # Lowest resistance above entry
            structural_tp = min(structural_targets)
            
            sl = structural_sl - (self.atr_buffer_mult * atr)
            tp = structural_tp - (self.atr_buffer_mult * atr / 2) # Front-run TP slightly
            
            sl_dist = entry - sl
            tp_dist = tp - entry
            
        else: # SELL
            # Lowest resistance above entry
            structural_sl = min(structural_stops)
            # Highest support below entry
            structural_tp = max(structural_targets)
            
            sl = structural_sl + (self.atr_buffer_mult * atr)
            tp = structural_tp + (self.atr_buffer_mult * atr / 2) # Front-run TP slightly
            
            sl_dist = sl - entry
            tp_dist = entry - tp

        if sl_dist <= 0 or tp_dist <= 0:
            return None
            
        rr = tp_dist / sl_dist
        
        invalidation_reason = None
        if sl_dist < (self.min_atr_sl_mult * atr):
            invalidation_reason = f"SL too tight (< {self.min_atr_sl_mult} ATR)"
        elif sl_dist > (self.max_atr_sl_mult * atr):
            invalidation_reason = f"SL too wide (> {self.max_atr_sl_mult} ATR)"
        elif rr < self.min_rr:
            invalidation_reason = f"R:R < {self.min_rr}"

        return TradeSetup(
            direction=direction,
            entry=entry,
            stop_loss=round(sl, 5),
            take_profit=round(tp, 5),
            reward_to_risk=round(rr, 2),
            invalidation_reason=invalidation_reason
        )
