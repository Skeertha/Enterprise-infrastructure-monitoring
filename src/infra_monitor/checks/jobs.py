from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from infra_monitor.alerting import Threshold, classify_numeric
from infra_monitor.models import CheckStatus, HealthResult, Severity, utc_now


class ScheduledJobCollector:
    """Treat a job heartbeat file's modification time as its last successful run."""

    def __init__(
        self,
        asset_id: str,
        job_name: str,
        heartbeat_file: str | Path,
        warning_age_minutes: float,
        critical_age_minutes: float,
    ):
        self.asset_id = asset_id
        self.job_name = job_name
        self.heartbeat_file = Path(heartbeat_file)
        self.threshold = Threshold(
            warning=float(warning_age_minutes), critical=float(critical_age_minutes)
        )

    def collect(self, observed_at: datetime | None = None) -> list[HealthResult]:
        timestamp = observed_at or utc_now()
        if not self.heartbeat_file.exists():
            status, severity = CheckStatus.CRITICAL, Severity.CRITICAL
            value: float | str = "missing"
            message = f"{self.job_name} heartbeat file is missing"
        else:
            modified = datetime.fromtimestamp(self.heartbeat_file.stat().st_mtime, tz=timezone.utc)
            age_minutes = max(0.0, (timestamp - modified).total_seconds() / 60)
            status, severity = classify_numeric(age_minutes, self.threshold)
            value = round(age_minutes, 2)
            message = f"{self.job_name} last successful heartbeat was {age_minutes:.1f} minutes ago"

        return [
            HealthResult(
                check_id=f"CHK-{uuid4().hex[:10].upper()}",
                asset_id=self.asset_id,
                check_type="SCHEDULED_JOB",
                metric="job_last_success_age",
                value=value,
                unit="minutes",
                status=status,
                severity=severity,
                message=message,
                observed_at=timestamp,
                metadata={
                    "job_name": self.job_name,
                    "heartbeat_file": str(self.heartbeat_file),
                },
            )
        ]
