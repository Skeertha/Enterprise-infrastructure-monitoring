from datetime import datetime, timedelta, timezone

from infra_monitor.incidents import IncidentManager
from infra_monitor.models import Asset, CheckStatus, HealthResult, Severity
from infra_monitor.storage import SQLiteStore


def result_at(timestamp, status, severity, message="CPU alert"):
    return HealthResult(
        check_id="CHK-001",
        asset_id="SRV-001",
        check_type="SYSTEM",
        metric="cpu_percent",
        value=95 if status == CheckStatus.CRITICAL else 40,
        unit="%",
        status=status,
        severity=severity,
        message=message,
        observed_at=timestamp,
    )


def create_store(tmp_path):
    store = SQLiteStore(tmp_path / "monitoring.db")
    store.initialize()
    store.upsert_asset(Asset("SRV-001", "server-01", "Server"))
    return store


def test_incident_is_created_deduplicated_escalated_and_resolved(tmp_path):
    store = create_store(tmp_path)
    manager = IncidentManager(store, {"CRITICAL": 15})
    start = datetime(2026, 9, 29, 8, 0, tzinfo=timezone.utc)

    incident_id = manager.process(result_at(start, CheckStatus.CRITICAL, Severity.CRITICAL))
    duplicate_id = manager.process(
        result_at(start + timedelta(minutes=5), CheckStatus.CRITICAL, Severity.CRITICAL)
    )

    assert incident_id == duplicate_id
    assert len(store.query("SELECT * FROM incidents")) == 1
    assert len(manager.escalate_due(start + timedelta(minutes=16))) == 1
    escalated = store.query("SELECT * FROM incidents")[0]
    assert escalated["status"] == "ESCALATED"
    assert escalated["escalation_level"] == 1

    manager.process(
        result_at(
            start + timedelta(minutes=20),
            CheckStatus.HEALTHY,
            Severity.INFO,
            "CPU returned to normal",
        )
    )
    resolved = store.query("SELECT * FROM incidents")[0]
    assert resolved["status"] == "RESOLVED"
    assert "Auto-resolved" in resolved["resolution"]

    events = store.query("SELECT event_type FROM incident_events ORDER BY id")
    assert [event["event_type"] for event in events] == [
        "CREATED",
        "REPEATED_ALERT",
        "ESCALATED",
        "RESOLVED",
    ]


def test_manual_acknowledge_and_resolution(tmp_path):
    store = create_store(tmp_path)
    manager = IncidentManager(store)
    start = datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc)
    incident_id = manager.process(result_at(start, CheckStatus.WARNING, Severity.HIGH))
    assert incident_id is not None

    assert manager.acknowledge(incident_id, start + timedelta(minutes=2))
    assert manager.resolve(
        incident_id,
        "Service restarted and validation passed",
        start + timedelta(minutes=8),
    )
    incident = store.query("SELECT * FROM incidents")[0]
    assert incident["status"] == "RESOLVED"
    assert incident["resolution"] == "Service restarted and validation passed"
