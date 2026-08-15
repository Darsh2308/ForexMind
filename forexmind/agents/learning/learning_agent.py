import json
import sqlite3
from datetime import datetime, timezone, timedelta
from forexmind.orchestration.market_context import MarketContext
from forexmind.agents.learning.schemas import LearningSnapshot
from forexmind.storage.db import fetch_resolved_recommendations

class LearningAgent:
    """
    Agent 14: Calculates recency-weighted win rates for specific market segments
    to calibrate the LLM's confidence score.
    """
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        
    def _extract_segment_key(self, context: MarketContext) -> str:
        """Derives a distinct string segment based on current market context.
        E.g., 'Bullish_London'
        """
        trend = "Neutral"
        if context.technical_analysis and context.technical_analysis.timeframes:
            first_tf = list(context.technical_analysis.timeframes.values())[0]
            if first_tf.trend == "bullish":
                trend = "Bullish"
            elif first_tf.trend == "bearish":
                trend = "Bearish"
                
        session = "Unknown"
        if context.market_data and context.market_data.sessions:
            if context.market_data.sessions.active_sessions:
                session = context.market_data.sessions.active_sessions[0].name
                
        return f"{trend}_{session}"
        
    def analyze(self, context: MarketContext) -> LearningSnapshot:
        segment_key = self._extract_segment_key(context)
        
        now = context.generated_at
        cutoff_30d = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        cutoff_90d = (now - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # We fetch all history and bucket it
        resolved = fetch_resolved_recommendations(self.conn)
        
        wins_30, total_30 = 0, 0
        wins_90, total_90 = 0, 0
        wins_life, total_life = 0, 0
        
        for row in resolved:
            try:
                hist_ctx_dict = json.loads(row["market_context_json"])
                hist_ctx = MarketContext.model_validate(hist_ctx_dict)
            except Exception:
                continue
                
            hist_segment = self._extract_segment_key(hist_ctx)
            if hist_segment != segment_key:
                continue
                
            status = row["status"]
            created_at = row["created_at"]
            
            is_win = (status == "WIN")
            
            total_life += 1
            if is_win: wins_life += 1
            
            if created_at >= cutoff_90d:
                total_90 += 1
                if is_win: wins_90 += 1
                
            if created_at >= cutoff_30d:
                total_30 += 1
                if is_win: wins_30 += 1
                
        wr_30 = (wins_30 / total_30) if total_30 > 0 else None
        wr_90 = (wins_90 / total_90) if total_90 > 0 else None
        wr_life = (wins_life / total_life) if total_life > 0 else None
        
        # Calculate recency-weighted confidence modifier
        # If we have 30d data, it heavily outweighs lifetime.
        modifier = 0.0
        active_wr = None
        
        if total_30 >= 5:
            active_wr = wr_30
        elif total_90 >= 10:
            active_wr = wr_90
        elif total_life >= 20:
            active_wr = wr_life
            
        if active_wr is not None:
            # Baseline is 50%. If win rate is 70%, modifier is +0.20
            modifier = active_wr - 0.50
            # Cap modifier
            modifier = max(-0.30, min(0.30, modifier))
            
        return LearningSnapshot(
            segment_key=segment_key,
            win_rate_30d=wr_30,
            win_rate_90d=wr_90,
            win_rate_lifetime=wr_life,
            confidence_modifier=round(modifier, 2),
            total_trades_analyzed=total_life
        )
