"""Dev-only: seeds a handful of recommendations spanning all four statuses
(PENDING/WIN/LOSS/EXPIRED) and both directions (BUY/SELL), so the frontend's
History view (Phase 3 of frontend/Development.md) can be verified against
real data instead of an empty table.

Not part of the production pipeline - the real pipeline only ever persists
BUY/SELL recommendations (see orchestration/graph.py::run_save_recommendation)
and starts every one of them as PENDING; WIN/LOSS/EXPIRED only happen later,
via the Evaluation Agent. This script writes directly to the same
`forexmind.db` file forexmind/api/app.py serves, so the frontend can query it
through the real API.

Safe to run more than once - each run just adds more demo rows.

Usage:
    python scripts/seed_demo_recommendations.py
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from forexmind.storage.db import get_connection, init_db, insert_recommendation

DB_PATH = Path("forexmind.db")  # matches forexmind/api/app.py's DB_PATH

# (minutes_ago, recommendation, entry, stop_loss, take_profit, status)
SEEDS = [
    (30, "BUY", 1.09850, 1.09600, 1.10350, "PENDING"),
    (60 * 6, "SELL", 1.10120, 1.10370, 1.09620, "WIN"),
    (60 * 20, "BUY", 1.08990, 1.08740, 1.09490, "LOSS"),
    (60 * 48, "SELL", 1.09500, 1.09750, 1.09000, "EXPIRED"),
    (5, "BUY", 1.09700, 1.09450, 1.10200, "PENDING"),
]


def main() -> None:
    init_db(DB_PATH)
    conn = get_connection(DB_PATH)
    now = datetime.now(timezone.utc)

    try:
        for minutes_ago, recommendation, entry, stop_loss, take_profit, status in SEEDS:
            created_at = (now - timedelta(minutes=minutes_ago)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            rec_id = insert_recommendation(
                conn,
                created_at=created_at,
                recommendation=recommendation,
                confidence=0.75,
                entry=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasoning="Seeded demo data for frontend History view verification.",
                status=status,
            )
            print(f"  #{rec_id}  {created_at}  {recommendation:<4} {status}")
    finally:
        conn.close()

    print(f"Seeded {len(SEEDS)} demo recommendations into {DB_PATH}.")


if __name__ == "__main__":
    main()
