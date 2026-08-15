import argparse
import requests
import json
import sys

API_URL = "http://localhost:8000/api"

def analyze(symbol: str):
    print(f"Triggering full AI pipeline analysis for {symbol}...\nThis may take 15-30 seconds.")
    try:
        resp = requests.post(f"{API_URL}/analyze", json={"symbol": symbol})
        resp.raise_for_status()
        data = resp.json()
        
        rec = data["recommendation"]
        print("\n" + "="*50)
        print(f" FOREXMIND AI RECOMMENDATION: {symbol}")
        print("="*50)
        print(f"Decision:    {rec['recommendation']}")
        print(f"Confidence:  {rec['confidence']*100:.0f}%")
        if rec['entry']:
            print(f"Entry:       {rec['entry']}")
            print(f"Take Profit: {rec['take_profit']}")
            print(f"Stop Loss:   {rec['stop_loss']}")
            
        print("\nREASONING:")
        print(rec['reasoning'])
        print("\n" + "="*50)
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the FastAPI server. Please ensure it is running on port 8000.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"API Error: {e.response.text}")
        sys.exit(1)

def history(limit: int):
    try:
        resp = requests.get(f"{API_URL}/history?limit={limit}")
        resp.raise_for_status()
        data = resp.json()
        
        recs = data.get("recommendations", [])
        if not recs:
            print("No recommendation history found.")
            return
            
        print(f"{'ID':<5} | {'Date':<20} | {'Decision':<10} | {'Status':<10} | {'Entry':<10} | {'TP':<10} | {'SL':<10}")
        print("-" * 85)
        for r in recs:
            print(f"{r['id']:<5} | {r['created_at']:<20} | {r['recommendation']:<10} | {r['status']:<10} | {r['entry'] or '-':<10} | {r['take_profit'] or '-':<10} | {r['stop_loss'] or '-':<10}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the FastAPI server. Please ensure it is running on port 8000.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="ForexMind AI Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Run a full pipeline analysis for a symbol")
    analyze_parser.add_argument("symbol", type=str, help="Currency pair symbol (e.g., EUR/USD)")
    
    # History command
    history_parser = subparsers.add_parser("history", help="View past recommendations")
    history_parser.add_argument("--limit", type=int, default=50, help="Number of records to fetch")
    
    args = parser.parse_args()
    
    if args.command == "analyze":
        analyze(args.symbol)
    elif args.command == "history":
        history(args.limit)

if __name__ == "__main__":
    main()
