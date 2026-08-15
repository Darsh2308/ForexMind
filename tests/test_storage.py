from forexmind.storage.db import fetch_candles, insert_candle


def test_init_db_creates_all_tables(db_conn):
    tables = {
        row["name"]
        for row in db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert {
        "candles",
        "recommendations",
        "agent_snapshots",
        "news_events",
        "evaluation_results",
    }.issubset(tables)


def test_insert_and_fetch_candle_roundtrip(db_conn):
    insert_candle(db_conn, "1day", "2024-01-02", 1.0950, 1.0960, 1.0944, 1.0959)

    rows = fetch_candles(db_conn, "1day")

    assert len(rows) == 1
    assert rows[0]["timestamp"] == "2024-01-02"
    assert rows[0]["close"] == 1.0959


def test_insert_candle_upsert_on_duplicate_timestamp(db_conn):
    insert_candle(db_conn, "1day", "2024-01-02", 1.0950, 1.0960, 1.0944, 1.0959)
    insert_candle(db_conn, "1day", "2024-01-02", 1.0950, 1.0999, 1.0944, 1.0990)

    rows = fetch_candles(db_conn, "1day")

    assert len(rows) == 1
    assert rows[0]["close"] == 1.0990


def test_fetch_candles_ordered_by_timestamp(db_conn, golden_candles):
    for candle in golden_candles:
        insert_candle(
            db_conn,
            "1day",
            candle["timestamp"],
            candle["open"],
            candle["high"],
            candle["low"],
            candle["close"],
            candle["volume"],
        )

    rows = fetch_candles(db_conn, "1day")

    assert len(rows) == len(golden_candles)
    timestamps = [row["timestamp"] for row in rows]
    assert timestamps == sorted(timestamps)
