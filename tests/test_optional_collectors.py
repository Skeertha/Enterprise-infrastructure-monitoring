from __future__ import annotations

import socket
import sys
import builtins
import json
import pytest
from contextlib import nullcontext
from types import ModuleType, SimpleNamespace

from infra_monitor.checks.cloud import CloudCLICollector
from infra_monitor.checks.database import SQLiteDatabaseCollector
from infra_monitor.checks.network import DNSCollector, IPCollector, NetworkInterfaceCollector, TCPCollector
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


@pytest.mark.parametrize(
    ("settings", "expected_message"),
    [
        ({"host": ""}, "Host must not be empty"),
        ({"host": " "}, "Host must not be empty"),
        ({"port": 0}, "Port must be between 1 and 65535"),
        ({"port": 65536}, "Port must be between 1 and 65535"),
        ({"timeout_seconds": 0}, "Timeout must be greater than zero"),
        ({"timeout_seconds": -1}, "Timeout must be greater than zero"),
        ({"warning_ms": -1}, "Critical threshold must be greater than warning threshold"),
        ({"warning_ms": 250, "critical_ms": 250}, "Critical threshold must be greater than warning threshold"),
    ],
)
def test_tcp_collector_rejects_invalid_settings(settings, expected_message):
    config = {"asset_id": "NET-001", "host": "localhost", "port": 443}
    config.update(settings)

    with pytest.raises(ValueError, match=expected_message):
        TCPCollector(**config)


@pytest.mark.parametrize(
    ("error", "expected_message"),
    [
        (socket.timeout("timed out"), "timed out"),
        (socket.gaierror(socket.EAI_NONAME, "DNS lookup failed"), "DNS resolution failed"),
        (ConnectionRefusedError("connection refused"), "connection refused"),
    ],
)
def test_tcp_collector_identifies_connection_errors(
    monkeypatch, error, expected_message
):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(
        "infra_monitor.checks.network.socket.create_connection",
        fail,
    )

    result = TCPCollector("NET-001", "example.test", 443).collect()[0]

    assert result.status == CheckStatus.CRITICAL
    assert result.value == "unreachable"
    assert expected_message.lower() in result.message.lower()

def test_ip_collector_accepts_ipv4():
    collector = IPCollector("NET-001", "192.168.1.1")
    assert collector.target == "192.168.1.1"


def test_ip_collector_accepts_ipv6():
    collector = IPCollector("NET-001", "2001:db8::1")
    assert collector.target == "2001:db8::1"


def test_ip_collector_rejects_invalid_ip():
    with pytest.raises(ValueError, match="valid IPv4 or IPv6"):
        IPCollector("NET-001", "not-an-ip")


def test_ip_collector_detects_reachable_host(monkeypatch):
    from types import ModuleType, SimpleNamespace

    monkeypatch.setattr(
        "infra_monitor.checks.network.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )

    result = IPCollector("NET-001", "127.0.0.1").collect()[0]

    assert result.status == CheckStatus.HEALTHY
    assert result.value == "reachable"
    assert result.metadata["ip_version"] == 4


def test_ip_collector_detects_unreachable_host(monkeypatch):
    from types import ModuleType, SimpleNamespace

    monkeypatch.setattr(
        "infra_monitor.checks.network.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1),
    )

    result = IPCollector("NET-001", "192.0.2.1").collect()[0]

    assert result.status == CheckStatus.CRITICAL
    assert result.value == "unreachable"


def test_ip_collector_handles_missing_ping(monkeypatch):
    def fail(*args, **kwargs):
        raise FileNotFoundError("ping not found")

    monkeypatch.setattr(
        "infra_monitor.checks.network.subprocess.run",
        fail,
    )

    result = IPCollector("NET-001", "127.0.0.1").collect()[0]

    assert result.status == CheckStatus.UNKNOWN
    assert result.value == "unknown"



def test_network_interface_collector_reads_interface_details(monkeypatch):
    import psutil
    import socket

    link_family = psutil.AF_LINK

    addresses = {
        "Wi-Fi": [
            SimpleNamespace(family=link_family, address="AA-BB-CC-DD-EE-FF"),
            SimpleNamespace(family=socket.AF_INET, address="192.0.2.10"),
            SimpleNamespace(family=socket.AF_INET6, address="fe80::1%12"),
        ],
        "Ethernet": [
            SimpleNamespace(family=socket.AF_INET, address="192.0.2.20"),
        ],
    }

    stats = {
        "Wi-Fi": SimpleNamespace(isup=True, speed=1000),
        "Ethernet": SimpleNamespace(isup=False, speed=0),
    }

    monkeypatch.setattr(
        "infra_monitor.checks.network.psutil.net_if_addrs",
        lambda: addresses,
    )
    monkeypatch.setattr(
        "infra_monitor.checks.network.psutil.net_if_stats",
        lambda: stats,
    )

    results = NetworkInterfaceCollector("NET-001").collect()

    assert len(results) == 2

    wifi = next(r for r in results if r.metadata["interface"] == "Wi-Fi")
    assert wifi.status == CheckStatus.HEALTHY
    assert wifi.metadata["mac_address"] == "AA-BB-CC-DD-EE-FF"
    assert "192.0.2.10" in wifi.metadata["ip_addresses"]
    assert "fe80::1" in wifi.metadata["ip_addresses"]
    assert wifi.metadata["speed_mbps"] == 1000

    ethernet = next(r for r in results if r.metadata["interface"] == "Ethernet")
    assert ethernet.status == CheckStatus.WARNING
    assert ethernet.value == "down"


def test_network_interface_collector_handles_no_interfaces(monkeypatch):
    monkeypatch.setattr(
        "infra_monitor.checks.network.psutil.net_if_addrs",
        lambda: {},
    )
    monkeypatch.setattr(
        "infra_monitor.checks.network.psutil.net_if_stats",
        lambda: {},
    )

    results = NetworkInterfaceCollector("NET-001").collect()

    assert results == []
def test_dns_collector_resolves_hostname(monkeypatch):
    import socket

    fake_records = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 0)),
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2001:db8::1", 0, 0, 0)),
    ]

    monkeypatch.setattr(
        "infra_monitor.checks.network.socket.getaddrinfo",
        lambda *args, **kwargs: fake_records,
    )

    results = DNSCollector("DNS-001", "example.com").collect()

    assert len(results) == 1
    assert results[0].status.value == "HEALTHY"
    assert results[0].value == "resolved"
    assert results[0].metadata["resolved_addresses"] == [
        "192.0.2.1",
        "2001:db8::1",
    ]


def test_dns_collector_handles_resolution_failure(monkeypatch):
    import socket

    def raise_dns_error(*args, **kwargs):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(
        "infra_monitor.checks.network.socket.getaddrinfo",
        raise_dns_error,
    )

    results = DNSCollector("DNS-001", "invalid.example").collect()

    assert len(results) == 1
    assert results[0].status.value == "CRITICAL"
    assert results[0].value == "unresolved"
    assert results[0].metadata["resolved_addresses"] == []
    assert results[0].metadata["record_count"] == 0

@pytest.mark.parametrize(
    ("elapsed_ms", "expected_status"),
    [
        (100, CheckStatus.HEALTHY),
        (300, CheckStatus.WARNING),
        (1100, CheckStatus.CRITICAL),
    ],
)
def test_tcp_collector_classifies_response_time(
    monkeypatch, elapsed_ms, expected_status
):
    monkeypatch.setattr(
        "infra_monitor.checks.network.socket.create_connection",
        lambda *args, **kwargs: nullcontext(),
    )

    ticks = iter([0.0, elapsed_ms / 1000])
    monkeypatch.setattr(
        "infra_monitor.checks.network.time.perf_counter",
        lambda: next(ticks),
    )

    result = TCPCollector(
        "NET-001",
        "localhost",
        443,
        warning_ms=250,
        critical_ms=1000,
    ).collect()[0]

    assert result.status == expected_status


def install_fake_vmware_sdk(monkeypatch, hosts):
    """Install fake VMware SDK modules for isolated collector tests."""
    disconnected = []
    destroyed = []

    class FakeView:
        view = hosts

        def Destroy(self):
            destroyed.append(True)

    class FakeViewManager:
        def CreateContainerView(self, root_folder, object_types, recursive):
            assert object_types == [vim_module.HostSystem]
            assert recursive is True
            return FakeView()

    class FakeServiceInstance:
        def RetrieveContent(self):
            return SimpleNamespace(
                rootFolder="fake-root",
                viewManager=FakeViewManager(),
            )

    service_instance = FakeServiceInstance()

    connect_module = ModuleType("pyVim.connect")
    connect_module.SmartConnect = lambda **kwargs: service_instance
    connect_module.Disconnect = lambda instance: disconnected.append(instance)

    pyvim_module = ModuleType("pyVim")
    pyvim_module.connect = connect_module

    vim_module = SimpleNamespace(HostSystem=object())
    pymomi_module = ModuleType("pyVmomi")
    pymomi_module.vim = vim_module

    monkeypatch.setitem(sys.modules, "pyVim", pyvim_module)
    monkeypatch.setitem(sys.modules, "pyVim.connect", connect_module)
    monkeypatch.setitem(sys.modules, "pyVmomi", pymomi_module)

    return service_instance, disconnected, destroyed


def test_vmware_collector_reports_healthy_hosts(monkeypatch):
    hosts = [
        SimpleNamespace(name="ESXi-01", overallStatus="green"),
        SimpleNamespace(name="ESXi-02", overallStatus="green"),
    ]
    service_instance, disconnected, destroyed = install_fake_vmware_sdk(
        monkeypatch, hosts
    )

    result = VMwareCollector(
        "VC-001", "vcenter.local", "readonly", "secret"
    ).collect()[0]

    assert result.status == CheckStatus.HEALTHY
    assert result.value == 0
    assert "All 2 VMware host(s) report green status" in result.message
    assert disconnected == [service_instance]
    assert destroyed == [True]


def test_vmware_collector_reports_unhealthy_hosts(monkeypatch):
    hosts = [
        SimpleNamespace(name="ESXi-01", overallStatus="green"),
        SimpleNamespace(name="ESXi-02", overallStatus="red"),
    ]
    service_instance, disconnected, destroyed = install_fake_vmware_sdk(
        monkeypatch, hosts
    )

    result = VMwareCollector(
        "VC-001", "vcenter.local", "readonly", "secret"
    ).collect()[0]

    assert result.status == CheckStatus.WARNING
    assert result.severity.value == "HIGH"
    assert result.value == 1
    assert "ESXi-02" in result.message
    assert disconnected == [service_instance]
    assert destroyed == [True]



def test_vmware_collector_handles_connection_failure(monkeypatch):
    install_fake_vmware_sdk(monkeypatch, [])

    connect_module = sys.modules["pyVim.connect"]

    def fail_connection(**kwargs):
        raise ConnectionError("vCenter is unreachable")

    monkeypatch.setattr(connect_module, "SmartConnect", fail_connection)

    result = VMwareCollector(
        "VC-001", "vcenter.local", "readonly", "secret"
    ).collect()[0]

    assert result.status == CheckStatus.CRITICAL
    assert result.value == "unavailable"
    assert "vCenter is unreachable" in result.message


def test_vmware_collector_disables_ssl_verification_when_configured(monkeypatch):
    import ssl

    hosts = [SimpleNamespace(name="ESXi-01", overallStatus="green")]
    service_instance, disconnected, destroyed = install_fake_vmware_sdk(
        monkeypatch, hosts
    )

    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return service_instance

    connect_module = sys.modules["pyVim.connect"]
    monkeypatch.setattr(connect_module, "SmartConnect", fake_connect)

    result = VMwareCollector(
        "VC-001",
        "vcenter.local",
        "readonly",
        "secret",
        port=8443,
        verify_ssl=False,
    ).collect()[0]

    assert result.status == CheckStatus.HEALTHY
    assert captured["host"] == "vcenter.local"
    assert captured["user"] == "readonly"
    assert captured["pwd"] == "secret"
    assert captured["port"] == 8443
    assert captured["sslContext"].check_hostname is False
    assert captured["sslContext"].verify_mode == ssl.CERT_NONE
    assert disconnected == [service_instance]
    assert destroyed == [True]


def test_ip_collector_uses_non_windows_ping_command(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        "infra_monitor.checks.network.platform.system",
        lambda: "Linux",
    )

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(
        "infra_monitor.checks.network.subprocess.run",
        fake_run,
    )

    result = IPCollector(
        "NET-001", "8.8.8.8", timeout_seconds=2
    ).collect()[0]

    assert result.status == CheckStatus.HEALTHY
    assert captured["command"] == ["ping", "-c", "1", "-W", "2", "8.8.8.8"]
    assert captured["kwargs"]["timeout"] == 3


def test_ip_collector_handles_ping_timeout(monkeypatch):
    import subprocess

    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ping", timeout=3)

    monkeypatch.setattr(
        "infra_monitor.checks.network.subprocess.run",
        fail,
    )

    result = IPCollector(
        "NET-001", "8.8.8.8"
    ).collect()[0]

    assert result.status == CheckStatus.CRITICAL
    assert result.value == "unreachable"
    assert "Ping timed out" in result.message


@pytest.mark.parametrize(
    ("target", "timeout_seconds", "expected_error"),
    [
        ("", 2, "IP address must not be empty"),
        ("127.0.0.1", 0, "Timeout must be greater than zero"),
        ("127.0.0.1", -1, "Timeout must be greater than zero"),
    ],
)
def test_ip_collector_rejects_invalid_settings(
    target, timeout_seconds, expected_error
):
    with pytest.raises(ValueError, match=expected_error):
        IPCollector(
            "NET-001",
            target,
            timeout_seconds=timeout_seconds,
        )


def test_network_interface_collector_respects_allowlist(monkeypatch):
    addresses = {
        "Wi-Fi": [],
        "Ethernet": [],
    }
    stats = {
        "Wi-Fi": SimpleNamespace(isup=True, speed=1000),
        "Ethernet": SimpleNamespace(isup=True, speed=1000),
    }

    monkeypatch.setattr(
        "infra_monitor.checks.network.psutil.net_if_addrs",
        lambda: addresses,
    )
    monkeypatch.setattr(
        "infra_monitor.checks.network.psutil.net_if_stats",
        lambda: stats,
    )

    results = NetworkInterfaceCollector(
        "NET-001",
        interface_names=["Wi-Fi"],
    ).collect()

    assert len(results) == 1
    assert results[0].metadata["interface"] == "Wi-Fi"


def test_dns_collector_rejects_empty_hostname():
    with pytest.raises(ValueError, match="Hostname must not be empty"):
        DNSCollector("DNS-001", " ")



def test_cloud_collector_reports_no_active_azure_alerts(monkeypatch):
    monkeypatch.setattr(
        "infra_monitor.checks.cloud.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        "infra_monitor.checks.cloud.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="[]",
            stderr="",
        ),
    )

    result = CloudCLICollector("azure", "AZ-001").collect()[0]

    assert result.status == CheckStatus.HEALTHY
    assert result.value == 0
    assert "No active AZURE monitoring alerts" in result.message

def test_tcp_collector_passes_connection_configuration(monkeypatch):
    captured = {}

    def fake_connection(address, timeout):
        captured["address"] = address
        captured["timeout"] = timeout
        return nullcontext()

    monkeypatch.setattr(
        "infra_monitor.checks.network.socket.create_connection",
        fake_connection,
    )

    TCPCollector(
        "NET-001",
        " example.com ",
        8443,
        timeout_seconds=5,
    ).collect()

    assert captured["address"] == ("example.com", 8443)
    assert captured["timeout"] == 5

def test_ip_collector_reports_ipv6_metadata(monkeypatch):
    monkeypatch.setattr(
        "infra_monitor.checks.network.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )

    result = IPCollector(
        "NET-001",
        "2001:db8::1",
    ).collect()[0]

    assert result.status == CheckStatus.HEALTHY
    assert result.value == "reachable"
    assert result.metadata["ip_address"] == "2001:db8::1"
    assert result.metadata["ip_version"] == 6
    assert result.metadata["protocol"] == "ICMP"

def test_network_interface_collector_handles_missing_stats(monkeypatch):
    monkeypatch.setattr(
        "infra_monitor.checks.network.psutil.net_if_addrs",
        lambda: {"Wi-Fi": []},
    )
    monkeypatch.setattr(
        "infra_monitor.checks.network.psutil.net_if_stats",
        lambda: {},
    )

    result = NetworkInterfaceCollector("NET-001").collect()[0]

    assert result.value == "down"
    assert result.status == CheckStatus.WARNING
    assert result.metadata["is_up"] is False
    assert result.metadata["speed_mbps"] is None

def test_dns_collector_removes_duplicate_addresses(monkeypatch):
    records = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.20", 0)),
    ]

    monkeypatch.setattr(
        "infra_monitor.checks.network.socket.getaddrinfo",
        lambda *args, **kwargs: records,
    )

    result = DNSCollector("DNS-001", "example.com").collect()[0]

    assert result.value == "resolved"
    assert result.metadata["resolved_addresses"] == [
        "192.0.2.10",
        "192.0.2.20",
    ]
    assert result.metadata["record_count"] == 2
