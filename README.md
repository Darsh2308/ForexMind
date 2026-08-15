# ForexMind AI

ForexMind AI is a fully autonomous, multi-agent algorithmic trading system. It orchestrates 14 distinct LangGraph agents to analyze market data, technical structure (SMC/ICT), news sentiment, and historical outcomes to generate highly calculated Forex trade recommendations.

## Prerequisites

1. **Python 3.11+**
2. Free API Keys for the following services:
   - **TwelveData** (Live & Historical OHLC market data)
   - **Finnhub** (Forex News & Economic Calendar)
   - **Groq** (LLM inference)

## Setup

1. **Clone and setup virtual environment:**
   ```bash
   git clone <repository_url>
   cd ForexMind
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Mac/Linux:
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   TWELVE_DATA_API_KEY="your_twelvedata_key_here"
   FINNHUB_API_KEY="your_finnhub_key_here"
   GROQ_API_KEY="your_groq_key_here"
   ```

## Running the System

### Option 1: Live API Server (Recommended)
ForexMind comes with a built-in FastAPI backend that exposes the LangGraph pipeline via a simple REST API.

1. **Start the API Server:**
   ```bash
   uvicorn forexmind.api.app:app --reload
   ```

2. **Use the CLI Client:**
   In a separate terminal, trigger a live market analysis using the CLI:
   ```bash
   python -m forexmind.cli analyze EUR/USD
   ```
   
3. **View Recommendation History:**
   The SQLite database tracks all AI recommendations. View past decisions:
   ```bash
   python -m forexmind.cli history
   ```

### Option 2: Backtesting
You can simulate the AI pipeline across historical data to validate its strategies. The backtester safely populates the SQLite database to avoid exhausting your TwelveData API limits.

```bash
# Simulate the last 7 days of the market, generating a trade every 4 hours
python -m forexmind.backtest --days 7 --interval 4
```
A detailed Markdown report containing win-rate statistics will be generated at `backtest_report.md`.

## System Architecture
- **Agents 1-6 (Deterministic):** Fetch market data, calculate indicators, find Support/Resistance, and map Smart Money Concepts (SMC).
- **Agents 7-11 (Context & Risk):** Overlay Elliott Wave, parse Finnhub News for sentiment, calculate Risk:Reward, and find structurally similar historical setups.
- **Agent 12 (Reasoning):** The Groq LLM digests the entire synthesized 'Blackboard' and outputs a final BUY/SELL/WAIT recommendation with Stop Loss and Take Profit bounds.
- **Agents 13-14 (Evaluation & Learning):** Automatically sweeps subsequent price action to score the AI's recommendations as WIN or LOSS. Computes recency-weighted statistics to dynamically adjust the AI's confidence score in the future.

## Built With
- **LangGraph & LangChain** for agent orchestration
- **FastAPI** for API serving
- **SQLite** for structural memory and evaluation logging
- **pandas-ta** for deterministic technical analysis
