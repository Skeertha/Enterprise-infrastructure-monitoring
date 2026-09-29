import os
from datetime import datetime, timedelta, timezone

from infra_monitor.checks.database import SQLiteDatabaseCollector
from infra_monitor.checks.jobs import ScheduledJobCollector
from infra_monitor.models import CheckStatus


def test_sqlite_database_collector(tmp_path):
    result = SQLiteDatabaseCollector("DB-001", tmp_path / "application.db").collect()[0]
    assert result.status == CheckStatus.HEALTHY
    assert result.metric == "database_response_time"


def test_scheduled_job_collector_detects_stale_heartbeat(tmp_path):
    heartbeat = tmp_path / "daily.ok"
    heartbeat.write_text("success", encoding="utf-8")
    now = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
    old = now - timedelta(minutes=100)
    os.utime(heartbeat, (old.timestamp(), old.timestamp()))

    result = ScheduledJobCollector(
        "JOB-001", "Daily Job", heartbeat, warning_age_minutes=60, critical_age_minutes=90
    ).collect(now)[0]

    assert result.status == CheckStatus.CRITICAL
    assert result.value == 100.0


def test_scheduled_job_collector_detects_missing_heartbeat(tmp_path):
    result = ScheduledJobCollector(
        "JOB-001",
        "Daily Job",
        tmp_path / "missing.ok",
        warning_age_minutes=60,
        critical_age_minutes=90,
    ).collect()[0]
    assert result.status == CheckStatus.CRITICAL
    assert result.value == "missing"
