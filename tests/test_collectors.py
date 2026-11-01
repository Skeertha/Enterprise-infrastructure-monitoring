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

def test_as_utc_iso_returns_none_for_none():
    from infra_monitor.models import as_utc_iso

    assert as_utc_iso(None) is None


def test_as_utc_iso_assigns_utc_to_naive_datetime():
    from infra_monitor.models import as_utc_iso

    naive_time = datetime(2026, 10, 31, 9, 30)

    result = as_utc_iso(naive_time)

    assert result == "2026-10-31T09:30:00+00:00"
