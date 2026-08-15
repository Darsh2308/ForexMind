import sqlite3
from forexmind.storage.db import (
    fetch_pending_recommendations,
    update_recommendation_status,
    fetch_candles_after
)

class EvaluationAgent:
    """
    Agent 13: Closes the loop by evaluating pending recommendations against
    actual price action to determine if they hit Take Profit (WIN) or Stop Loss (LOSS).
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def evaluate_all(self, current_time: str, interval: str = "15min"):
        """
        Sweeps the database for all PENDING recommendations and evaluates them.
        `current_time` is used to limit the sweep, or simply provides a reference.
        """
        pending_recs = fetch_pending_recommendations(self.conn)
        
        for rec in pending_recs:
            rec_id = rec["id"]
            direction = rec["recommendation"]
            entry = rec["entry"]
            sl = rec["stop_loss"]
            tp = rec["take_profit"]
            created_at = rec["created_at"]
            
            # Fetch candles that occurred after the recommendation was generated
            # We limit to 1000 candles to prevent infinite sweep if it's a very old trade
            # that never hit SL/TP (we might want to EXPIRE those later).
            candles = fetch_candles_after(self.conn, interval=interval, as_of=created_at, limit=1000)
            
            outcome = None
            
            for candle in candles:
                high = candle["high"]
                low = candle["low"]
                
                if direction == "BUY":
                    # Check SL first (pessimistic evaluation)
                    if low <= sl:
                        outcome = "LOSS"
                        break
                    if high >= tp:
                        outcome = "WIN"
                        break
                        
                elif direction == "SELL":
                    if high >= sl:
                        outcome = "LOSS"
                        break
                    if low <= tp:
                        outcome = "WIN"
                        break
                        
            if outcome:
                update_recommendation_status(self.conn, rec_id, outcome)
