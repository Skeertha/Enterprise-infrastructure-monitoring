PRAGMA foreign_keys = ON;

CREATE TABLE assets (
    asset_id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    operating_system TEXT NOT NULL,
    environment TEXT NOT NULL,
    owner TEXT NOT NULL,
    ip_address TEXT,
    location TEXT,
    criticality TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE health_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_id TEXT NOT NULL,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    check_type TEXT NOT NULL,
    metric TEXT NOT NULL,
    value TEXT,
    unit TEXT,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE incidents (
    incident_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    check_id TEXT NOT NULL,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    acknowledged_at TEXT,
    resolved_at TEXT,
    resolution TEXT,
    escalation_level INTEGER NOT NULL DEFAULT 0,
    last_updated_at TEXT NOT NULL
);

CREATE TABLE incident_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL REFERENCES incidents(incident_id),
    event_type TEXT NOT NULL,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL
);

