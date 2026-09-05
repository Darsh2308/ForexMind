"""Dev-only: produces one recommendation backed by a REAL, full MarketContext
(every deterministic/rule-based agent actually runs against real historical
candles) so the frontend's evidence drill-down (Phase 4 of
frontend/Development.md) has something genuine to render.

Only the final verdict is fabricated - there is no configured Groq/Ollama key
in this environment, so the Reasoning Agent can't be run for real here. That
one section is built from the *real* Risk Analysis Agent's own computed
buy/sell setup (whichever direction it actually found this run), following
the same rule the real Reasoning Agent is instructed to follow: no valid
setup means WAIT, not a fabricated trade.

Requires candles already backfilled somewhere on disk (see
scripts/backfill_market_data.py) - this script copies them into
forexmind.db (the file forexmind/api/app.py actually serves) from
var/forexmind.db if forexmind.db doesn't have any yet, rather than
re-fetching from Twelve Data.

Usage:
    python scripts/seed_demo_recommendation_with_context.py
"""

from datetime import datetime, timezone
from pathlib import Path

from forexmind.agents.reasoning.schemas import ReasoningSnapshot
from forexmind.orchestration.graph import (
    fetch_market_data,
    run_candlestick,
    run_cross_validate,
    run_elliott_wave,
    run_historical_similarity,
    run_learning_agent,
    run_news,
    run_price_action,
    run_risk_analysis,
    run_smc,
    run_support_resistance,
    run_technical_analysis,
    run_wyckoff,
)
from forexmind.storage.db import get_connection, init_db, insert_agent_snapshot, insert_recommendation

DB_PATH = Path("forexmind.db")  # matches forexmind/api/app.py's DB_PATH
SOURCE_CANDLES_DB = Path("var/forexmind.db")  # populated by backfill_market_data.py


def _ensure_candles(conn) -> None:
    count = conn.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
    if count > 0:
        print(f"  {DB_PATH} already has {count} candles, skipping copy.")
        return
    if not SOURCE_CANDLES_DB.exists():
        raise SystemExit(
            f"No candles in {DB_PATH} and {SOURCE_CANDLES_DB} doesn't exist either - "
            "run scripts/backfill_market_data.py first."
        )
    conn.execute("ATTACH DATABASE ? AS src", (str(SOURCE_CANDLES_DB),))
    conn.execute(
        "INSERT INTO candles (interval, timestamp, open, high, low, close, volume) "
        "SELECT interval, timestamp, open, high, low, close, volume FROM src.candles"
    )
    conn.commit()
    conn.execute("DETACH DATABASE src")
    copied = conn.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
    print(f"  Copied {copied} candles from {SOURCE_CANDLES_DB} into {DB_PATH}.")


def main() -> None:
    init_db(DB_PATH)
    conn = get_connection(DB_PATH)

    print("Preparing candle data...")
    _ensure_candles(conn)

    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = {"conn": conn, "as_of": as_of, "symbol": "EUR/USD", "timeframes": ["15min", "1h", "4h"]}

    print("Running the real deterministic agents against real candles...")
    state.update(fetch_market_data(state))
    state.update(run_technical_analysis(state))
    state.update(run_price_action(state))
    state.update(run_candlestick(state))
    state.update(run_support_resistance(state))
    state.update(run_smc(state))
    state.update(run_elliott_wave(state))
    state.update(run_wyckoff(state))
    state.update(run_news(state))
    state.update(run_cross_validate(state))
    state.update(run_historical_similarity(state))
    state.update(run_risk_analysis(state))
    state.update(run_learning_agent(state))

    context = state["market_context"]
    risk = context.risk_analysis

    # The one fabricated section: follow the real Reasoning Agent's own rule
    # (Risk Analysis flags a valid setup, or the answer is WAIT) instead of
    # inventing a trade that Risk Analysis didn't actually find.
    setup = None
    recommendation = "WAIT"
    if risk and risk.buy_setup and risk.buy_setup.invalidation_reason is None:
        setup, recommendation = risk.buy_setup, "BUY"
    elif risk and risk.sell_setup and risk.sell_setup.invalidation_reason is None:
        setup, recommendation = risk.sell_setup, "SELL"

    context.reasoning_output = ReasoningSnapshot(
        recommendation=recommendation,
        confidence=0.78 if setup else 0.0,
        entry=setup.entry if setup else None,
        stop_loss=setup.stop_loss if setup else None,
        take_profit=setup.take_profit if setup else None,
        reasoning=(
            f"Demo seed for the frontend evidence drill-down: every section below "
            f"besides this final call is a real Risk/SMC/TA/etc. agent output "
            f"computed against real historical candles. {'Risk Analysis found a valid ' + recommendation + ' setup, taken as-is.' if setup else 'Risk Analysis found no valid setup this run, so WAIT.'}"
        ),
        supporting_evidence=(["Risk Analysis found a structurally valid setup"] if setup else []),
        conflicting_evidence=context.conflicts,
        historical_similarity=(
            context.historical_similarity.top_similar[0].similarity_score
            if context.historical_similarity and context.historical_similarity.top_similar
            else None
        ),
        reward_to_risk=setup.reward_to_risk if setup else None,
        important_news=[],
        trade_quality_score=7 if setup else 1,
        llm_provider="groq",
    )

    rec = context.reasoning_output
    rec_id = insert_recommendation(
        conn,
        created_at=as_of,
        recommendation=rec.recommendation,
        confidence=rec.confidence,
        entry=rec.entry,
        stop_loss=rec.stop_loss,
        take_profit=rec.take_profit,
        reasoning=rec.reasoning,
        status="PENDING",
    )
    insert_agent_snapshot(
        conn,
        recommendation_id=rec_id,
        agent_name="market_context",
        payload=context.model_dump_json(exclude_none=True, exclude_defaults=True),
        created_at=as_of,
    )

    print(f"\nSeeded recommendation #{rec_id}: {rec.recommendation} (populated sections: {context.populated_sections()})")


if __name__ == "__main__":
    main()
