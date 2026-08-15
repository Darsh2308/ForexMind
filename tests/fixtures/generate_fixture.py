"""Regenerates eurusd_sample.csv: a deterministic (seeded), synthetic daily
EUR/USD OHLC series used by offline tests so they never depend on network
access or a real Twelve Data API key. Not collected by pytest (no test_
prefix); run manually with `python tests/fixtures/generate_fixture.py` if the
fixture ever needs to change shape.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUTPUT_PATH = Path(__file__).resolve().parent / "eurusd_sample.csv"
NUM_DAYS = 90
START_DATE = date(2024, 1, 2)
START_PRICE = 1.0950


def generate_rows() -> list[dict]:
    rng = random.Random(42)
    rows = []
    close = START_PRICE
    current_date = START_DATE
    for _ in range(NUM_DAYS):
        if current_date.weekday() >= 5:  # skip weekends, forex convention
            current_date += timedelta(days=1)
            continue
        open_ = close
        drift = rng.uniform(-0.0035, 0.0035)
        close = round(open_ + drift, 5)
        high = round(max(open_, close) + rng.uniform(0, 0.0020), 5)
        low = round(min(open_, close) - rng.uniform(0, 0.0020), 5)
        rows.append(
            {
                "timestamp": current_date.isoformat(),
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": "",
            }
        )
        current_date += timedelta(days=1)
    return rows


def main() -> None:
    rows = generate_rows()
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
