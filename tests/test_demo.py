from datetime import datetime, timedelta, timezone

from infra_monitor.checks.demo import DEMO_ASSETS, DemoCollector
from infra_monitor.incidents import IncidentManager
from infra_monitor.storage import SQLiteStore


def test_demo_exercises_incident_lifecycle(tmp_path):
    store = SQLiteStore(tmp_path / "demo.db")
    store.initialize()
    store.upsert_assets(DEMO_ASSETS)
    manager = IncidentManager(store)
    collector = DemoCollector()
    start = datetime(2026, 9, 29, 0, 0, tzinfo=timezone.utc)

    for cycle in range(12):
        timestamp = start + timedelta(minutes=cycle * 20)
        for result in collector.collect(cycle, timestamp):
            store.record_health_result(result)
            manager.process(result)
        manager.escalate_due(timestamp)

    incidents = store.query("SELECT * FROM incidents")
    assert len(incidents) == 8
    assert all(incident["status"] == "RESOLVED" for incident in incidents)
    assert any(incident["escalation_level"] > 0 for incident in incidents)
    assert len(store.query("SELECT * FROM health_checks")) == 96
