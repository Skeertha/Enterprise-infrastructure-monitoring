from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from infra_monitor.models import CheckStatus, HealthResult, Severity, utc_now


class SQLiteDatabaseCollector:
    def __init__(self, asset_id: str, database_path: str | Path, timeout_seconds: float = 3):
        self.asset_id = asset_id
        self.database_path = Path(database_path)
        self.timeout_seconds = float(timeout_seconds)

    def collect(self, observed_at: datetime | None = None) -> list[HealthResult]:
        timestamp = observed_at or utc_now()
        started = time.perf_counter()
        try:
            connection = sqlite3.connect(self.database_path, timeout=self.timeout_seconds)
            try:
                connection.execute("SELECT 1").fetchone()
            finally:
                connection.close()
            elapsed_ms = (time.perf_counter() - started) * 1000
            status, severity = CheckStatus.HEALTHY, Severity.INFO
            message = f"Database query completed in {elapsed_ms:.1f} ms"
            value: float | str = round(elapsed_ms, 2)
        except sqlite3.Error as error:
            status, severity = CheckStatus.CRITICAL, Severity.CRITICAL
            message = f"Database availability check failed: {error}"
            value = "unavailable"

        return [
            HealthResult(
                check_id=f"CHK-{uuid4().hex[:10].upper()}",
                asset_id=self.asset_id,
                check_type="DATABASE",
                metric="database_response_time",
                value=value,
                unit="ms",
                status=status,
                severity=severity,
                message=message,
                observed_at=timestamp,
                metadata={"database": str(self.database_path)},
            )
        ]
