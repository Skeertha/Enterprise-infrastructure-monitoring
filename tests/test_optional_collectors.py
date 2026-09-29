from __future__ import annotations

import builtins
import json
from contextlib import nullcontext
from types import SimpleNamespace

from infra_monitor.checks.cloud import CloudCLICollector
from infra_monitor.checks.database import SQLiteDatabaseCollector
from infra_monitor.checks.network import TCPCollector
from infra_monitor.checks.system import SystemCollector
from infra_monitor.checks.vmware import VMwareCollector
from infra_monitor.models import CheckStatus


def test_network_collector_success_and_failure(monkeypatch):
    monkeypatch.setattr(
        "infra_monitor.checks.network.socket.create_connection",
        lambda *args, **kwargs: nullcontext(),
    )
    success = TCPCollector("NET-001", "localhost", 443).collect()[0]
    assert success.status == CheckStatus.HEALTHY

    def fail(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr("infra_monitor.checks.network.socket.create_connection", fail)
    failure = TCPCollector("NET-001", "localhost", 443).collect()[0]
    assert failure.status == CheckStatus.CRITICAL
    assert failure.value == "unreachable"


def test_system_collector_uses_thresholds(monkeypatch):
    monkeypatch.setattr("infra_monitor.checks.system.psutil.cpu_percent", lambda interval: 95)
    monkeypatch.setattr(
        "infra_monitor.checks.system.psutil.virtual_memory",
        lambda: SimpleNamespace(percent=45),
    )
    monkeypatch.setattr(
        "infra_monitor.checks.system.psutil.disk_usage",
        lambda path: SimpleNamespace(percent=82),
    )
    results = SystemCollector("SRV-001", disk_path="/").collect()
    assert [result.status for result in results] == [
        CheckStatus.CRITICAL,
        CheckStatus.HEALTHY,
        CheckStatus.WARNING,
    ]


def test_database_collector_failure(tmp_path):
    result = SQLiteDatabaseCollector("DB-001", tmp_path).collect()[0]
    assert result.status == CheckStatus.CRITICAL
    assert result.value == "unavailable"


def test_cloud_collector_handles_missing_cli(monkeypatch):
    monkeypatch.setattr("infra_monitor.checks.cloud.shutil.which", lambda name: None)
    result = CloudCLICollector("aws", "AWS-001").collect()[0]
    assert result.status == CheckStatus.UNKNOWN


def test_cloud_collectors_parse_provider_responses(monkeypatch):
    monkeypatch.setattr("infra_monitor.checks.cloud.shutil.which", lambda name: f"/usr/bin/{name}")

    def completed(command, **kwargs):
        if command[0] == "aws":
            payload = {"MetricAlarms": [{"AlarmName": "CPU"}], "CompositeAlarms": []}
        else:
            payload = [{"name": "Disk", "enabled": True}, {"name": "Old", "enabled": False}]
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("infra_monitor.checks.cloud.subprocess.run", completed)
    assert CloudCLICollector("aws", "AWS-001").collect()[0].value == 1
    assert CloudCLICollector("azure", "AZ-001").collect()[0].value == 1


def test_cloud_collector_reports_command_error(monkeypatch):
    monkeypatch.setattr("infra_monitor.checks.cloud.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        "infra_monitor.checks.cloud.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="denied"),
    )
    result = CloudCLICollector("aws", "AWS-001").collect()[0]
    assert result.status == CheckStatus.CRITICAL
    assert "denied" in result.message


def test_cloud_collector_validates_provider():
    try:
        CloudCLICollector("gcp", "GCP-001")
    except ValueError as error:
        assert "provider" in str(error)
    else:
        raise AssertionError("Unsupported provider was accepted")


def test_vmware_collector_handles_missing_sdk(monkeypatch):
    original_import = builtins.__import__

    def controlled_import(name, *args, **kwargs):
        if name.startswith("pyVim") or name.startswith("pyVmomi"):
            raise ImportError("SDK not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", controlled_import)
    result = VMwareCollector("VC-001", "vcenter.local", "readonly", "secret").collect()[0]
    assert result.status == CheckStatus.UNKNOWN
