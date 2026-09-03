import sqlite3
from unittest.mock import patch, MagicMock

from forexmind.monitoring.alerts import send_alert
from forexmind.storage.db import get_connection, init_db, fetch_recent_alerts, count_alerts_since


def _fresh_conn(tmp_path):
    db_path = tmp_path / "alerts.db"
    init_db(db_path)
    return get_connection(db_path)


def test_send_alert_persists_to_db(tmp_path):
    conn = _fresh_conn(tmp_path)

    send_alert(source="news", message="Finnhub timed out", severity="warning", conn=conn)

    rows = fetch_recent_alerts(conn)
    assert len(rows) == 1
    assert rows[0]["source"] == "news"
    assert rows[0]["severity"] == "warning"
    assert "Finnhub timed out" in rows[0]["message"]


def test_send_alert_never_raises_on_bad_connection():
    bad_conn = MagicMock(spec=sqlite3.Connection)
    bad_conn.execute.side_effect = sqlite3.OperationalError("db is locked")

    # Must not raise even though persisting the alert itself fails.
    send_alert(source="reasoning", message="LLM down", severity="critical", conn=bad_conn)


def test_send_alert_posts_webhook_when_configured(tmp_path):
    conn = _fresh_conn(tmp_path)

    with patch.dict("os.environ", {"ALERT_WEBHOOK_URL": "https://hooks.example.com/x"}):
        with patch("forexmind.monitoring.alerts.requests.post") as mock_post:
            send_alert(source="smc", message="detector crashed", severity="warning", conn=conn)
            mock_post.assert_called_once()
            _, kwargs = mock_post.call_args
            assert "smc" in kwargs["json"]["text"]


def test_send_alert_swallows_webhook_failure(tmp_path):
    conn = _fresh_conn(tmp_path)

    with patch.dict("os.environ", {"ALERT_WEBHOOK_URL": "https://hooks.example.com/x"}):
        with patch("forexmind.monitoring.alerts.requests.post", side_effect=ConnectionError("no network")):
            # Must not raise even though the webhook delivery itself fails.
            send_alert(source="smc", message="detector crashed", severity="warning", conn=conn)


def test_count_alerts_since(tmp_path):
    conn = _fresh_conn(tmp_path)
    send_alert(source="news", message="x", severity="warning", conn=conn)
    send_alert(source="smc", message="y", severity="critical", conn=conn)

    assert count_alerts_since(conn, "2000-01-01T00:00:00Z") == 2
    assert count_alerts_since(conn, "2999-01-01T00:00:00Z") == 0
