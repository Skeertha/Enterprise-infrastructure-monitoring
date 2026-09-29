import csv
from datetime import datetime, timedelta, timezone

from infra_monitor.incidents import IncidentManager
from infra_monitor.models import Asset, CheckStatus, HealthResult, Severity
from infra_monitor.reporting import PowerBIExporter
from infra_monitor.storage import SQLiteStore


def test_power_bi_export_contains_operational_datasets(tmp_path):
    store = SQLiteStore(tmp_path / "monitoring.db")
    store.initialize()
    store.upsert_asset(Asset("SRV-001", "server-01", "Server"))
    manager = IncidentManager(store)
    opened = datetime(2026, 9, 29, 6, 0, tzinfo=timezone.utc)

    alert = HealthResult(
        "CHK-001",
        "SRV-001",
        "SYSTEM",
        "disk_percent",
        93,
        "%",
        CheckStatus.CRITICAL,
        Severity.CRITICAL,
        "Disk is 93% full",
        opened,
    )
    recovered = HealthResult(
        "CHK-002",
        "SRV-001",
        "SYSTEM",
        "disk_percent",
        72,
        "%",
        CheckStatus.HEALTHY,
        Severity.INFO,
        "Disk is 72% full",
        opened + timedelta(minutes=10),
    )
    for result in (alert, recovered):
        store.record_health_result(result)
        manager.process(result)

    paths = PowerBIExporter(store, tmp_path / "exports").export_all()
    assert len(paths) == 6
    assert all(path.exists() for path in paths)

    with (tmp_path / "exports" / "incidents.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["status"] == "RESOLVED"
    assert rows[0]["sla_met"] == "1"
