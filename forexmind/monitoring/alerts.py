"""Phase 17 pipeline alerting: logs, persists to SQLite, and optionally pushes
to a webhook (Slack/Discord-compatible incoming webhook) when ALERT_WEBHOOK_URL
is set. Best-effort throughout - alerting must never raise, since it is called
from exception handlers reporting on a failure that has already happened."""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone

import requests

from forexmind.storage.db import insert_pipeline_alert

logger = logging.getLogger("forexmind.alerts")


def send_alert(
    source: str,
    message: str,
    severity: str = "warning",
    conn: sqlite3.Connection | None = None,
) -> None:
    """Records a pipeline failure or degradation event."""
    log_fn = logger.error if severity == "critical" else logger.warning
    log_fn("ALERT [%s] %s: %s", severity.upper(), source, message)

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if conn is not None:
        try:
            insert_pipeline_alert(
                conn, created_at=created_at, source=source, severity=severity, message=message
            )
        except Exception:
            logger.exception("Failed to persist alert to database")

    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if webhook_url:
        try:
            requests.post(
                webhook_url,
                json={"text": f"[ForexMind AI] {severity.upper()} in {source}: {message}"},
                timeout=5,
            )
        except Exception:
            logger.exception("Failed to deliver alert webhook")
