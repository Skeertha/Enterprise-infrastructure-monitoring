from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from infra_monitor.checks.cloud import CloudCLICollector
from infra_monitor.checks.database import SQLiteDatabaseCollector
from infra_monitor.checks.jobs import ScheduledJobCollector
from infra_monitor.checks.network import TCPCollector
from infra_monitor.checks.system import SystemCollector
from infra_monitor.checks.vmware import VMwareCollector
from infra_monitor.incidents import IncidentManager
from infra_monitor.models import Asset, HealthResult
from infra_monitor.storage import SQLiteStore


class Collector(Protocol):
    def collect(self, observed_at: datetime | None = None) -> list[HealthResult]: ...


def assets_from_config(config: dict[str, Any]) -> list[Asset]:
    return [
        Asset(
            asset_id=str(item["asset_id"]),
            hostname=str(item["hostname"]),
            asset_type=str(item.get("asset_type", "Server")),
            operating_system=str(item.get("operating_system", "Unknown")),
            environment=str(item.get("environment", "Lab")),
            owner=str(item.get("owner", "Infrastructure Operations")),
            ip_address=str(item.get("ip_address", "")),
            location=str(item.get("location", "Lab")),
            criticality=str(item.get("criticality", "Medium")),
            status=str(item.get("status", "Active")),
        )
        for item in config.get("assets", [])
    ]


def build_collectors(config: dict[str, Any]) -> list[Collector]:
    collectors: list[Collector] = []
    settings = config.get("collectors", {})

    system = settings.get("system", {})
    if system.get("enabled", False):
        collectors.append(
            SystemCollector(
                asset_id=str(system["asset_id"]),
                thresholds=config.get("thresholds", {}),
                disk_path=system.get("disk_path"),
            )
        )

    for item in settings.get("tcp", []):
        if item.get("enabled", True):
            collectors.append(
                TCPCollector(
                    asset_id=str(item["asset_id"]),
                    host=str(item["host"]),
                    port=int(item["port"]),
                    timeout_seconds=float(item.get("timeout_seconds", 2)),
                    warning_ms=float(item.get("warning_ms", 250)),
                    critical_ms=float(item.get("critical_ms", 1000)),
                )
            )

    for item in settings.get("sqlite", []):
        if item.get("enabled", True):
            collectors.append(
                SQLiteDatabaseCollector(
                    asset_id=str(item["asset_id"]),
                    database_path=Path(str(item["database_path"])),
                    timeout_seconds=float(item.get("timeout_seconds", 3)),
                )
            )

    for item in settings.get("scheduled_jobs", []):
        if item.get("enabled", True):
            collectors.append(
                ScheduledJobCollector(
                    asset_id=str(item["asset_id"]),
                    job_name=str(item["job_name"]),
                    heartbeat_file=Path(str(item["heartbeat_file"])),
                    warning_age_minutes=float(item.get("warning_age_minutes", 60)),
                    critical_age_minutes=float(item.get("critical_age_minutes", 90)),
                )
            )

    for item in settings.get("cloud", []):
        if item.get("enabled", False):
            collectors.append(
                CloudCLICollector(
                    provider=str(item["provider"]),
                    asset_id=str(item["asset_id"]),
                    timeout_seconds=int(item.get("timeout_seconds", 20)),
                )
            )

    vmware = settings.get("vmware", {})
    if vmware.get("enabled", False):
        collectors.append(
            VMwareCollector(
                asset_id=str(vmware["asset_id"]),
                host=str(vmware["host"]),
                username=str(vmware["username"]),
                password=str(vmware["password"]),
                port=int(vmware.get("port", 443)),
                verify_ssl=bool(vmware.get("verify_ssl", True)),
            )
        )
    return collectors


class MonitoringRunner:
    def __init__(
        self,
        store: SQLiteStore,
        incident_manager: IncidentManager,
        collectors: list[Collector],
    ):
        self.store = store
        self.incident_manager = incident_manager
        self.collectors = collectors

    def run_once(self, observed_at: datetime | None = None) -> list[HealthResult]:
        results: list[HealthResult] = []
        for collector in self.collectors:
            for result in collector.collect(observed_at):
                self.store.record_health_result(result)
                self.incident_manager.process(result)
                results.append(result)
        self.incident_manager.escalate_due(observed_at)
        return results
