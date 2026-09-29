from __future__ import annotations

import platform
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import psutil

from infra_monitor.alerting import Threshold, classify_numeric, threshold_from_config
from infra_monitor.models import HealthResult, utc_now

DEFAULTS = {
    "cpu_percent": Threshold(warning=80, critical=90),
    "memory_percent": Threshold(warning=80, critical=90),
    "disk_percent": Threshold(warning=80, critical=90),
}


class SystemCollector:
    def __init__(
        self,
        asset_id: str,
        thresholds: dict[str, dict[str, float | str]] | None = None,
        disk_path: str | None = None,
    ):
        self.asset_id = asset_id
        self.thresholds = thresholds or {}
        self.disk_path = disk_path or (Path.home().anchor or "/")

    def _result(
        self,
        metric: str,
        value: float,
        unit: str,
        observed_at: datetime,
    ) -> HealthResult:
        threshold = threshold_from_config(self.thresholds, metric, DEFAULTS[metric])
        status, severity = classify_numeric(value, threshold)
        return HealthResult(
            check_id=f"CHK-{uuid4().hex[:10].upper()}",
            asset_id=self.asset_id,
            check_type="SYSTEM",
            metric=metric,
            value=round(value, 2),
            unit=unit,
            status=status,
            severity=severity,
            message=(
                f"{metric.replace('_', ' ').title()} is {value:.1f}{unit} ({status.value.lower()})"
            ),
            observed_at=observed_at,
            metadata={"platform": platform.platform(), "disk_path": self.disk_path},
        )

    def collect(self, observed_at: datetime | None = None) -> list[HealthResult]:
        timestamp = observed_at or utc_now()
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage(self.disk_path).percent
        return [
            self._result("cpu_percent", cpu, "%", timestamp),
            self._result("memory_percent", memory, "%", timestamp),
            self._result("disk_percent", disk, "%", timestamp),
        ]
