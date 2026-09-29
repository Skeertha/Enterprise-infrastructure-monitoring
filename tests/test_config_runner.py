from __future__ import annotations

from datetime import datetime, timezone

import pytest

from infra_monitor.config import load_config, project_path
from infra_monitor.incidents import IncidentManager
from infra_monitor.models import Asset, CheckStatus, HealthResult, Severity
from infra_monitor.runner import MonitoringRunner, assets_from_config, build_collectors
from infra_monitor.storage import SQLiteStore


def test_configuration_expands_environment_and_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_HOST", "lab.example.local")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "host: ${LAB_HOST}\nusername: ${LAB_USER:-readonly}\nitems:\n  - ${LAB_PORT:-443}\n",
        encoding="utf-8",
    )

    config = load_config(config_path)
    assert config == {
        "host": "lab.example.local",
        "username": "readonly",
        "items": ["443"],
    }


def test_configuration_rejects_missing_file_variable_and_non_mapping(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.yaml")

    missing_variable = tmp_path / "missing-variable.yaml"
    missing_variable.write_text("password: ${REQUIRED_TEST_PASSWORD}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="REQUIRED_TEST_PASSWORD"):
        load_config(missing_variable)

    list_config = tmp_path / "list.yaml"
    list_config.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        load_config(list_config)


def test_project_path_and_asset_mapping(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert project_path({}, "database_path", "data/test.db") == tmp_path / "data/test.db"
    absolute = tmp_path / "absolute.db"
    assert project_path({"database_path": str(absolute)}, "database_path", "unused") == absolute

    assets = assets_from_config(
        {
            "assets": [
                {
                    "asset_id": "SRV-001",
                    "hostname": "server-01",
                    "asset_type": "Server",
                    "criticality": "High",
                }
            ]
        }
    )
    assert assets[0].asset_id == "SRV-001"
    assert assets[0].environment == "Lab"


def test_build_collectors_respects_enabled_flags(tmp_path):
    config = {
        "collectors": {
            "system": {"enabled": True, "asset_id": "SRV-001"},
            "tcp": [
                {
                    "enabled": True,
                    "asset_id": "NET-001",
                    "host": "localhost",
                    "port": 443,
                }
            ],
            "sqlite": [
                {
                    "enabled": True,
                    "asset_id": "DB-001",
                    "database_path": str(tmp_path / "application.db"),
                }
            ],
            "scheduled_jobs": [
                {
                    "enabled": True,
                    "asset_id": "JOB-001",
                    "job_name": "Daily Job",
                    "heartbeat_file": str(tmp_path / "daily.ok"),
                }
            ],
            "cloud": [{"enabled": True, "provider": "aws", "asset_id": "AWS-001"}],
            "vmware": {
                "enabled": True,
                "asset_id": "VC-001",
                "host": "vcenter.local",
                "username": "readonly",
                "password": "secret",
            },
        }
    }
    assert len(build_collectors(config)) == 6


class DummyCollector:
    def collect(self, observed_at=None):
        return [
            HealthResult(
                "CHK-001",
                "SRV-001",
                "SYSTEM",
                "cpu_percent",
                42,
                "%",
                CheckStatus.HEALTHY,
                Severity.INFO,
                "CPU is healthy",
                observed_at or datetime.now(timezone.utc),
            )
        ]


def test_monitoring_runner_persists_collector_results(tmp_path):
    store = SQLiteStore(tmp_path / "monitoring.db")
    store.initialize()
    store.upsert_asset(Asset("SRV-001", "server-01", "Server"))
    runner = MonitoringRunner(store, IncidentManager(store), [DummyCollector()])
    results = runner.run_once(datetime(2026, 9, 29, tzinfo=timezone.utc))
    assert len(results) == 1
    assert len(store.query("SELECT * FROM health_checks")) == 1
