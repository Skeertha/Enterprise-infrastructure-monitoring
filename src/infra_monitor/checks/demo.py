from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from infra_monitor.alerting import Threshold, classify_numeric
from infra_monitor.models import Asset, CheckStatus, HealthResult, Severity

DEMO_ASSETS = [
    Asset("SRV-WIN-01", "win-app-01", "Server", "Windows Server 2022", criticality="High"),
    Asset("SRV-LNX-01", "lnx-api-01", "Server", "Ubuntu 24.04", criticality="High"),
    Asset("DB-SQL-01", "sql-orders-01", "Database", "SQL Server", criticality="Critical"),
    Asset("NET-FW-01", "edge-fw-01", "Network Device", "Firewall OS", criticality="Critical"),
    Asset("CLOUD-AZ-01", "azure-production", "Cloud", "Azure", criticality="High"),
    Asset("VMW-VC-01", "vcenter-lab-01", "Virtualization", "VMware", criticality="High"),
    Asset("JOB-JDE-01", "jde-daily-batch", "Scheduled Job", "JDE", criticality="High"),
]


SERIES = {
    "cpu": [42, 48, 55, 84, 93, 95, 87, 71, 58, 49, 45, 43],
    "memory": [57, 61, 64, 68, 72, 83, 91, 86, 76, 68, 62, 58],
    "disk": [69, 72, 75, 79, 83, 88, 92, 94, 89, 78, 74, 71],
    "latency": [38, 42, 55, 88, 265, 1250, 780, 310, 140, 74, 51, 43],
    "db_available": [1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1],
    "cloud_alerts": [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    "vmware_unhealthy": [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "job_age": [12, 14, 18, 25, 44, 72, 96, 121, 18, 13, 11, 10],
}


class DemoCollector:
    def _numeric(
        self,
        asset_id: str,
        check_type: str,
        metric: str,
        value: float,
        unit: str,
        threshold: Threshold,
        observed_at: datetime,
    ) -> HealthResult:
        status, severity = classify_numeric(value, threshold)
        return HealthResult(
            check_id=f"CHK-DEMO-{uuid4().hex[:8].upper()}",
            asset_id=asset_id,
            check_type=check_type,
            metric=metric,
            value=value,
            unit=unit,
            status=status,
            severity=severity,
            message=f"{metric.replace('_', ' ').title()} measured {value}{unit}",
            observed_at=observed_at,
            metadata={"source": "deterministic-demo"},
        )

    def collect(self, cycle: int, observed_at: datetime) -> list[HealthResult]:
        index = cycle % len(SERIES["cpu"])
        results = [
            self._numeric(
                "SRV-WIN-01",
                "SYSTEM",
                "cpu_percent",
                SERIES["cpu"][index],
                "%",
                Threshold(80, 90),
                observed_at,
            ),
            self._numeric(
                "SRV-WIN-01",
                "SYSTEM",
                "memory_percent",
                SERIES["memory"][index],
                "%",
                Threshold(80, 90),
                observed_at,
            ),
            self._numeric(
                "SRV-LNX-01",
                "SYSTEM",
                "disk_percent",
                SERIES["disk"][index],
                "%",
                Threshold(80, 90),
                observed_at,
            ),
            self._numeric(
                "NET-FW-01",
                "NETWORK",
                "latency_ms",
                SERIES["latency"][index],
                "ms",
                Threshold(250, 1000),
                observed_at,
            ),
            self._numeric(
                "CLOUD-AZ-01",
                "CLOUD",
                "active_cloud_alerts",
                SERIES["cloud_alerts"][index],
                " alerts",
                Threshold(1, 3),
                observed_at,
            ),
            self._numeric(
                "VMW-VC-01",
                "VMWARE",
                "unhealthy_hosts",
                SERIES["vmware_unhealthy"][index],
                " hosts",
                Threshold(1, 3),
                observed_at,
            ),
            self._numeric(
                "JOB-JDE-01",
                "SCHEDULED_JOB",
                "job_last_success_age",
                SERIES["job_age"][index],
                " min",
                Threshold(60, 90),
                observed_at,
            ),
        ]

        available = SERIES["db_available"][index]
        db_status = CheckStatus.HEALTHY if available else CheckStatus.CRITICAL
        db_severity = Severity.INFO if available else Severity.CRITICAL
        results.append(
            HealthResult(
                check_id=f"CHK-DEMO-{uuid4().hex[:8].upper()}",
                asset_id="DB-SQL-01",
                check_type="DATABASE",
                metric="database_availability",
                value=available,
                unit="boolean",
                status=db_status,
                severity=db_severity,
                message="Database is available" if available else "Database connection failed",
                observed_at=observed_at,
                metadata={"source": "deterministic-demo"},
            )
        )
        return results
