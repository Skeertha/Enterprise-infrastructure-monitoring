from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from infra_monitor.storage import SQLiteStore

EXPORT_QUERIES = {
    "assets.csv": "SELECT * FROM assets ORDER BY asset_id",
    "health_checks.csv": "SELECT * FROM health_checks ORDER BY observed_at, id",
    "incidents.csv": """
        SELECT *,
            CASE WHEN resolved_at IS NOT NULL
                THEN ROUND((julianday(resolved_at) - julianday(opened_at)) * 1440, 2)
                ELSE NULL END AS resolution_minutes,
            CASE WHEN resolved_at IS NOT NULL AND datetime(resolved_at) <= datetime(due_at) THEN 1
                 WHEN resolved_at IS NULL AND datetime('now') <= datetime(due_at) THEN 1
                 ELSE 0 END AS sla_met
        FROM incidents ORDER BY opened_at
    """,
    "incident_events.csv": "SELECT * FROM incident_events ORDER BY created_at, id",
    "daily_status.csv": """
        SELECT
            substr(observed_at, 1, 10) AS report_date,
            COUNT(*) AS total_checks,
            SUM(CASE WHEN status = 'HEALTHY' THEN 1 ELSE 0 END) AS healthy_checks,
            SUM(CASE WHEN status = 'WARNING' THEN 1 ELSE 0 END) AS warning_checks,
            SUM(CASE WHEN status = 'CRITICAL' THEN 1 ELSE 0 END) AS critical_checks,
            ROUND(100.0 * SUM(CASE WHEN status = 'HEALTHY' THEN 1 ELSE 0 END) / COUNT(*), 2)
                AS health_percentage
        FROM health_checks
        GROUP BY substr(observed_at, 1, 10)
        ORDER BY report_date
    """,
    "sla_summary.csv": """
        SELECT
            severity,
            COUNT(*) AS total_incidents,
            SUM(CASE WHEN status = 'RESOLVED' THEN 1 ELSE 0 END) AS resolved_incidents,
            SUM(CASE WHEN status IN ('OPEN', 'ACKNOWLEDGED', 'ESCALATED') THEN 1 ELSE 0 END)
                AS active_incidents,
            SUM(CASE WHEN escalation_level > 0 THEN 1 ELSE 0 END) AS breached_incidents,
            ROUND(AVG(CASE WHEN resolved_at IS NOT NULL
                THEN (julianday(resolved_at) - julianday(opened_at)) * 1440 END), 2)
                AS avg_resolution_minutes
        FROM incidents
        GROUP BY severity
        ORDER BY CASE severity
            WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3
            WHEN 'LOW' THEN 4 ELSE 5 END
    """,
}


class PowerBIExporter:
    def __init__(self, store: SQLiteStore, output_directory: str | Path):
        self.store = store
        self.output_directory = Path(output_directory)

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def export_all(self) -> list[Path]:
        exported: list[Path] = []
        for filename, query in EXPORT_QUERIES.items():
            path = self.output_directory / filename
            self._write_csv(path, self.store.query(query))
            exported.append(path)
        return exported
