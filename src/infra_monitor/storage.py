from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from infra_monitor.models import Asset, HealthResult, Incident, as_utc_iso

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS assets (
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

CREATE TABLE IF NOT EXISTS health_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    check_type TEXT NOT NULL,
    metric TEXT NOT NULL,
    value TEXT,
    unit TEXT,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);

CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    check_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
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
    last_updated_at TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);

CREATE TABLE IF NOT EXISTS incident_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
);

CREATE INDEX IF NOT EXISTS idx_checks_asset_time
    ON health_checks(asset_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_checks_status
    ON health_checks(status, observed_at);
CREATE INDEX IF NOT EXISTS idx_incidents_fingerprint_status
    ON incidents(fingerprint, status);
CREATE INDEX IF NOT EXISTS idx_incidents_due
    ON incidents(status, due_at);
"""


class SQLiteStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def upsert_asset(self, asset: Asset) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO assets (
                    asset_id, hostname, asset_type, operating_system, environment,
                    owner, ip_address, location, criticality, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_id) DO UPDATE SET
                    hostname=excluded.hostname,
                    asset_type=excluded.asset_type,
                    operating_system=excluded.operating_system,
                    environment=excluded.environment,
                    owner=excluded.owner,
                    ip_address=excluded.ip_address,
                    location=excluded.location,
                    criticality=excluded.criticality,
                    status=excluded.status,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    asset.asset_id,
                    asset.hostname,
                    asset.asset_type,
                    asset.operating_system,
                    asset.environment,
                    asset.owner,
                    asset.ip_address,
                    asset.location,
                    asset.criticality,
                    asset.status,
                ),
            )

    def upsert_assets(self, assets: Iterable[Asset]) -> None:
        for asset in assets:
            self.upsert_asset(asset)

    def record_health_result(self, result: HealthResult) -> None:
        record = result.to_record()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO health_checks (
                    check_id, asset_id, check_type, metric, value, unit, status,
                    severity, message, observed_at, metadata_json
                ) VALUES (
                    :check_id, :asset_id, :check_type, :metric, :value, :unit,
                    :status, :severity, :message, :observed_at, :metadata_json
                )
                """,
                record,
            )

    def find_active_incident(self, fingerprint: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM incidents
                WHERE fingerprint = ? AND status IN ('OPEN', 'ACKNOWLEDGED', 'ESCALATED')
                ORDER BY opened_at DESC LIMIT 1
                """,
                (fingerprint,),
            ).fetchone()

    def create_incident(self, incident: Incident) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO incidents (
                    incident_id, fingerprint, check_id, asset_id, title, description,
                    severity, status, opened_at, due_at, acknowledged_at, resolved_at,
                    resolution, escalation_level, last_updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident.incident_id,
                    incident.fingerprint,
                    incident.check_id,
                    incident.asset_id,
                    incident.title,
                    incident.description,
                    incident.severity.value,
                    incident.status,
                    as_utc_iso(incident.opened_at),
                    as_utc_iso(incident.due_at),
                    as_utc_iso(incident.acknowledged_at),
                    as_utc_iso(incident.resolved_at),
                    incident.resolution,
                    incident.escalation_level,
                    as_utc_iso(incident.last_updated_at),
                ),
            )

    def update_active_incident(
        self,
        incident_id: str,
        *,
        description: str,
        severity: str,
        updated_at: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE incidents
                SET description = ?, severity = ?, last_updated_at = ?
                WHERE incident_id = ?
                """,
                (description, severity, updated_at, incident_id),
            )

    def resolve_incident(
        self,
        incident_id: str,
        resolved_at: str,
        resolution: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE incidents
                SET status='RESOLVED', resolved_at=?, resolution=?, last_updated_at=?
                WHERE incident_id=?
                """,
                (resolved_at, resolution, resolved_at, incident_id),
            )

    def acknowledge_incident(self, incident_id: str, acknowledged_at: str) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE incidents
                SET status='ACKNOWLEDGED', acknowledged_at=?, last_updated_at=?
                WHERE incident_id=? AND status IN ('OPEN', 'ESCALATED')
                """,
                (acknowledged_at, acknowledged_at, incident_id),
            )
            return cursor.rowcount > 0

    def manually_resolve_incident(
        self, incident_id: str, resolved_at: str, resolution: str
    ) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE incidents
                SET status='RESOLVED', resolved_at=?, resolution=?, last_updated_at=?
                WHERE incident_id=? AND status IN ('OPEN', 'ACKNOWLEDGED', 'ESCALATED')
                """,
                (resolved_at, resolution, resolved_at, incident_id),
            )
            return cursor.rowcount > 0

    def list_due_incidents(self, now_iso: str) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT * FROM incidents
                    WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'ESCALATED') AND due_at <= ?
                    ORDER BY due_at
                    """,
                    (now_iso,),
                ).fetchall()
            )

    def escalate_incident(
        self,
        incident_id: str,
        escalation_level: int,
        next_due_at: str,
        updated_at: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE incidents
                SET status='ESCALATED', escalation_level=?, due_at=?, last_updated_at=?
                WHERE incident_id=?
                """,
                (escalation_level, next_due_at, updated_at, incident_id),
            )

    def add_incident_event(
        self,
        incident_id: str,
        event_type: str,
        details: str,
        created_at: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO incident_events (incident_id, event_type, details, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (incident_id, event_type, details, created_at),
            )

    def query(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, parameters).fetchall()]
