import argparse
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from forexmind.agents.market_data.twelve_data_client import TwelveDataClient
from forexmind.agents.market_data.market_data_agent import MarketDataAgent
from forexmind.orchestration.graph import create_analysis_graph
from forexmind.storage.db import get_connection, init_db, fetch_all_recommendations
from forexmind.agents.evaluation.evaluation_agent import EvaluationAgent

def run_backtest(days: int, interval_hours: int, symbol: str = "EUR/USD"):
    db_path = Path("forexmind.db")
    init_db(db_path)
    conn = get_connection(db_path)
    
    # 1. Backfill Market Data
    print(f"--- Starting Backtest for {symbol} over {days} days ---")
    api_key = os.getenv("TWELVE_DATA_API_KEY", "dummy")
    if api_key != "dummy":
        print("Backfilling historical data from TwelveData... (this uses ~8 requests)")
        client = TwelveDataClient(api_key=api_key)
        market_agent = MarketDataAgent(client=client, conn=conn)
        # 2000 outputsize covers roughly 2.7 years for Daily, 11 months for 4h, 83 days for 1h.
        market_agent.backfill_all_timeframes(outputsize=2000)
    else:
        print("WARNING: TWELVE_DATA_API_KEY is not set. Assuming database is already populated.")

    # 2. Simulation Loop
    graph = create_analysis_graph()
    
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc - timedelta(days=days)
    
    current_time = start_time
    total_steps = int((days * 24) / interval_hours)
    step = 1
    
    trades_generated = 0
    waits_generated = 0
    
    print("\n--- Running LangGraph Simulation ---")
    while current_time <= now_utc:
        as_of_str = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"[{step}/{total_steps}] Analyzing as of {as_of_str}...")
        
        initial_state = {
            "conn": conn,
            "as_of": as_of_str,
            "symbol": symbol
        }
        
        try:
            result = graph.invoke(initial_state)
            context = result["market_context"]
            if context.reasoning_output:
                rec = context.reasoning_output.recommendation
                if rec in ("BUY", "SELL"):
                    trades_generated += 1
                    print(f"  -> Generated {rec} signal! (Confidence: {context.reasoning_output.confidence:.2f})")
                else:
                    waits_generated += 1
                    print("  -> WAIT")
        except Exception as e:
            print(f"  -> Error during execution: {e}")
            
        current_time += timedelta(hours=interval_hours)
        step += 1
        
        # Sleep to respect Groq rate limits (30 RPM = 2 seconds per req, 3 seconds is safe)
        time.sleep(3)

    # 3. Auto-Evaluation
    print("\n--- Evaluating Recommendations ---")
    eval_agent = EvaluationAgent(conn=conn)
    eval_agent.evaluate_all(current_time=now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"))
    print("Evaluation complete.")

    # 4. Reporting
    print("\n--- Generating Report ---")
    rows = fetch_all_recommendations(conn, limit=1000)
    
    wins = 0
    losses = 0
    pending = 0
    expired = 0
    
    high_conf_wins = 0
    high_conf_losses = 0
    
    # We only want to analyze trades that were created within this backtest window
    # Actually, fetch_all_recommendations gets everything, so let's filter in Python
    backtest_start_iso = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    valid_rows = []
    for row in rows:
        if row["created_at"] >= backtest_start_iso:
            valid_rows.append(row)
            if row["status"] == "WIN":
                wins += 1
            elif row["status"] == "LOSS":
                losses += 1
            elif row["status"] == "PENDING":
                pending += 1
            else:
                expired += 1
                
            # If we had stored confidence in the recommendation row, we could segment here.
            # But we didn't add confidence to the main SELECT in DB, though it is in the schema!
            # row["confidence"] is available.
            if row["status"] == "WIN" and row.get("confidence", 0) >= 0.70:
                high_conf_wins += 1
            elif row["status"] == "LOSS" and row.get("confidence", 0) >= 0.70:
                high_conf_losses += 1

    total_resolved = wins + losses
    win_rate = (wins / total_resolved) * 100 if total_resolved > 0 else 0.0
    
    high_conf_total = high_conf_wins + high_conf_losses
    high_conf_win_rate = (high_conf_wins / high_conf_total) * 100 if high_conf_total > 0 else 0.0

    report = f"""# ForexMind AI — Backtest Report ({symbol})

**Window:** {days} Days ({start_time.strftime('%Y-%m-%d')} to {now_utc.strftime('%Y-%m-%d')})
**Interval:** Every {interval_hours} Hours

## Summary Statistics
- **Total Trades Generated:** {trades_generated}
- **Total WAITS Generated:** {waits_generated}
- **Total Resolved (WIN/LOSS):** {total_resolved}
- **Pending/Unresolved:** {pending}

## Performance
- **Overall Win Rate:** {win_rate:.1f}% ({wins} W / {losses} L)
- **High Confidence (>70%) Win Rate:** {high_conf_win_rate:.1f}% ({high_conf_wins} W / {high_conf_losses} L)

*Report generated on: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""

    report_path = Path("backtest_report.md")
    report_path.write_text(report, encoding="utf-8")
    
    print(report)
    print(f"\nReport saved to {report_path.absolute()}")
    
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ForexMind AI Backtester")
    parser.add_argument("--days", type=int, default=7, help="Number of historical days to simulate")
    parser.add_argument("--interval", type=int, default=4, help="Hours to skip between iterations")
    parser.add_argument("--symbol", type=str, default="EUR/USD", help="Currency pair symbol")
    
    args = parser.parse_args()
    run_backtest(args.days, args.interval, args.symbol)
