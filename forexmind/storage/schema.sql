-- ForexMind AI v1 schema (EUR/USD only, no multi-pair columns by design).

CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interval TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL,
    UNIQUE(interval, timestamp)
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    recommendation TEXT NOT NULL CHECK(recommendation IN ('BUY', 'SELL', 'WAIT')),
    confidence REAL,
    entry REAL,
    stop_loss REAL,
    take_profit REAL,
    horizon TEXT,
    reasoning TEXT,
    supporting_evidence TEXT,
    conflicting_evidence TEXT,
    historical_similarity TEXT,
    risk_reward REAL,
    important_news TEXT,
    trade_quality_score REAL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'WIN', 'LOSS', 'EXPIRED')),
    expires_at TEXT,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id INTEGER REFERENCES recommendations(id),
    agent_name TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time TEXT NOT NULL,
    title TEXT NOT NULL,
    currency TEXT,
    impact TEXT,
    sentiment TEXT,
    source TEXT,
    raw_payload TEXT
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id INTEGER NOT NULL REFERENCES recommendations(id),
    outcome TEXT NOT NULL CHECK(outcome IN ('WIN', 'LOSS', 'EXPIRED')),
    evaluated_at TEXT NOT NULL,
    exit_price REAL,
    notes TEXT
);

-- Phase 17 hardening: records pipeline node failures/degradations so they are
-- queryable (basic monitoring) instead of only living in log files.
CREATE TABLE IF NOT EXISTS pipeline_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('warning', 'critical')),
    message TEXT NOT NULL
);
