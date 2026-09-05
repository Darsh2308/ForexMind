from contextlib import asynccontextmanager

import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os

from forexmind.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CandlesResponse,
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    RecommendationDetailResponse,
    RecommendationHistoryItem,
)
from forexmind.agents.chat.chat_agent import ChatAgent
from forexmind.orchestration.graph import create_analysis_graph
from forexmind.storage.db import (
    get_connection,
    init_db,
    fetch_all_recommendations,
    fetch_candles_before,
    fetch_market_context_payload,
    fetch_recommendation_by_id,
    count_alerts_since,
)

# We will initialize a persistent DB in the project root
DB_PATH = Path("forexmind.db")

# Comma-separated list of allowed browser origins for the frontend (Vite's
# default dev ports by default). Tightened to the real deployed frontend
# origin in Phase 8 of frontend/Development.md - this dev-time default is
# intentionally permissive to unblock local development.
_DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [
    origin.strip()
    for origin in (os.environ.get("CORS_ORIGINS") or _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(DB_PATH)
    yield


app = FastAPI(title="ForexMind AI", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
graph = create_analysis_graph()
chat_agent = ChatAgent()


@app.get("/health")
def health() -> dict:
    """Basic Phase 17 monitoring: confirms the DB is reachable and surfaces
    how many pipeline_alerts (agent/LLM failures) were recorded in the last
    24h, so a human or uptime check can notice a degraded pipeline."""
    try:
        conn = get_connection(DB_PATH)
        try:
            since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
            alerts_last_24h = count_alerts_since(conn, since)
        finally:
            conn.close()
        return {"status": "ok", "alerts_last_24h": alerts_last_24h}
    except Exception as e:
        return {"status": "degraded", "detail": str(e)}

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(request: AnalyzeRequest):
    conn = get_connection(DB_PATH)
    try:
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        initial_state = {
            "conn": conn,
            "as_of": now_utc,
            "symbol": request.symbol.upper()
        }
        
        result = graph.invoke(initial_state)
        
        context = result["market_context"]
        if not context.reasoning_output:
            raise HTTPException(status_code=500, detail="Reasoning Agent failed to produce an output.")
            
        return AnalyzeResponse(
            symbol=context.symbol,
            as_of=now_utc,
            recommendation=context.reasoning_output,
            conflicts=context.conflicts
        )
    finally:
        conn.close()

@app.get("/api/recommendation/{rec_id}", response_model=RecommendationDetailResponse)
def recommendation_detail_endpoint(rec_id: int):
    """Phase 4 (frontend/Development.md): exposes the full stored blackboard
    for one past recommendation, not just the summary fields /api/history
    returns."""
    conn = get_connection(DB_PATH)
    try:
        rec = fetch_recommendation_by_id(conn, rec_id)
        if rec is None:
            raise HTTPException(status_code=404, detail=f"No recommendation with id {rec_id}.")

        payload = fetch_market_context_payload(conn, rec_id)
        if payload is None:
            raise HTTPException(
                status_code=404,
                detail=f"No stored market context for recommendation {rec_id}.",
            )

        return RecommendationDetailResponse(
            id=rec["id"],
            created_at=rec["created_at"],
            status=rec["status"],
            market_context=json.loads(payload),
        )
    finally:
        conn.close()

_CHAT_FRESHNESS_WINDOW = timedelta(minutes=15)


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """Grounded chat about a recommendation's MarketContext.

    Two modes:
    - `recommendation_id` given: chat about that specific past call (original
      dashboard drill-down behavior) - 404s if it or its stored context is missing.
    - `recommendation_id` omitted: "cold" chat. Grounds itself in the latest
      recommendation if one exists and is younger than
      `_CHAT_FRESHNESS_WINDOW`; otherwise runs the analysis graph inline to get
      a fresh MarketContext before answering, so a WAIT verdict (never
      persisted, see run_save_recommendation in orchestration/graph.py) can
      still ground an answer.
    """
    conn = get_connection(DB_PATH)
    try:
        rec_id = request.recommendation_id
        triggered_new_analysis = False

        if rec_id is not None:
            rec = fetch_recommendation_by_id(conn, rec_id)
            if rec is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No recommendation with id {rec_id}.",
                )
            context_json = fetch_market_context_payload(conn, rec_id)
            if context_json is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No stored market context for recommendation {rec_id}.",
                )
        else:
            latest = fetch_all_recommendations(conn, limit=1)
            latest_row = latest[0] if latest else None
            is_fresh = False
            if latest_row is not None:
                created_at = datetime.strptime(
                    latest_row["created_at"], "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=timezone.utc)
                is_fresh = (datetime.now(timezone.utc) - created_at) < _CHAT_FRESHNESS_WINDOW

            if latest_row is not None and is_fresh:
                rec_id = latest_row["id"]
                context_json = fetch_market_context_payload(conn, rec_id)
            else:
                now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                result = graph.invoke({"conn": conn, "as_of": now_utc, "symbol": "EUR/USD"})
                context = result["market_context"]
                if not context.reasoning_output:
                    raise HTTPException(
                        status_code=500,
                        detail="Reasoning Agent failed to produce an output.",
                    )
                context_json = context.model_dump_json(exclude_none=True, exclude_defaults=True)
                triggered_new_analysis = True
                if context.reasoning_output.recommendation in ("BUY", "SELL"):
                    saved = fetch_all_recommendations(conn, limit=1)
                    rec_id = saved[0]["id"] if saved else None
    finally:
        conn.close()

    history = [(m.role, m.content) for m in request.history]
    reply, provider = chat_agent.reply(context_json=context_json, message=request.message, history=history)
    return ChatResponse(
        reply=reply,
        llm_provider=provider,
        recommendation_id=rec_id,
        triggered_new_analysis=triggered_new_analysis,
    )

@app.get("/api/candles", response_model=CandlesResponse)
def candles_endpoint(interval: str = "15min", as_of: str | None = None, limit: int = 200):
    """Phase 5 (frontend/Development.md): OHLC for the price chart. Same
    lookahead-safe read the analysis agents themselves use - `as_of` never
    returns a candle that closes after it."""
    as_of_value = as_of or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = get_connection(DB_PATH)
    try:
        rows = fetch_candles_before(conn, interval, as_of_value, limit=limit)
        return CandlesResponse(
            interval=interval,
            candles=[
                {
                    "timestamp": row["timestamp"],
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"],
                }
                for row in rows
            ],
        )
    finally:
        conn.close()

@app.get("/api/history", response_model=HistoryResponse)
def history_endpoint(limit: int = 50):
    conn = get_connection(DB_PATH)
    try:
        rows = fetch_all_recommendations(conn, limit=limit)
        items = []
        for row in rows:
            items.append(RecommendationHistoryItem(
                id=row["id"],
                created_at=row["created_at"],
                recommendation=row["recommendation"],
                entry=row["entry"],
                stop_loss=row["stop_loss"],
                take_profit=row["take_profit"],
                status=row["status"]
            ))
        return HistoryResponse(recommendations=items)
    finally:
        conn.close()
