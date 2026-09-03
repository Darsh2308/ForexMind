from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os

from forexmind.api.schemas import AnalyzeRequest, AnalyzeResponse, HistoryResponse, RecommendationHistoryItem
from forexmind.orchestration.graph import create_analysis_graph
from forexmind.storage.db import get_connection, init_db, fetch_all_recommendations, count_alerts_since

# We will initialize a persistent DB in the project root
DB_PATH = Path("forexmind.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(DB_PATH)
    yield


app = FastAPI(title="ForexMind AI", lifespan=lifespan)
graph = create_analysis_graph()


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
