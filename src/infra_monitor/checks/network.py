from __future__ import annotations

import ipaddress
import platform
import socket
import subprocess
import time
from datetime import datetime
from uuid import uuid4

import psutil

from infra_monitor.alerting import Threshold, classify_numeric
from infra_monitor.models import CheckStatus, HealthResult, Severity, utc_now


class TCPCollector:
    def __init__(
        self,
        asset_id: str,
        host: str,
        port: int,
        timeout_seconds: float = 2.0,
        warning_ms: float = 250,
        critical_ms: float = 1000,
    ):
        if not host or not host.strip():
            raise ValueError("Host must not be empty")

        port = int(port)
        timeout_seconds = float(timeout_seconds)
        warning_ms = float(warning_ms)
        critical_ms = float(critical_ms)

        if not 1 <= port <= 65535:
            raise ValueError("Port must be between 1 and 65535")

        if timeout_seconds <= 0:
            raise ValueError("Timeout must be greater than zero")

        if warning_ms < 0 or critical_ms <= warning_ms:
            raise ValueError("Critical threshold must be greater than warning threshold")

        self.asset_id = asset_id
        self.host = host.strip()
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.threshold = Threshold(warning=float(warning_ms), critical=float(critical_ms))

    def collect(self, observed_at: datetime | None = None) -> list[HealthResult]:
        timestamp = observed_at or utc_now()
        started = time.perf_counter()
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout_seconds):
                pass
            elapsed_ms = (time.perf_counter() - started) * 1000
            status, severity = classify_numeric(elapsed_ms, self.threshold)
            message = f"TCP {self.host}:{self.port} responded in {elapsed_ms:.1f} ms"
            value: float | str = round(elapsed_ms, 2)
        except socket.timeout as error:
            status, severity = CheckStatus.CRITICAL, Severity.CRITICAL
            message = f"TCP connection timed out for {self.host}:{self.port}: {error}"
            value = "unreachable"
        except socket.gaierror as error:
            status, severity = CheckStatus.CRITICAL, Severity.CRITICAL
            message = f"DNS resolution failed for {self.host}: {error}"
            value = "unreachable"
        except ConnectionRefusedError as error:
            status, severity = CheckStatus.CRITICAL, Severity.CRITICAL
            message = f"TCP connection refused by {self.host}:{self.port}: {error}"
            value = "unreachable"
        except OSError as error:
            status, severity = CheckStatus.CRITICAL, Severity.CRITICAL
            message = f"TCP {self.host}:{self.port} is unavailable: {error}"
            value = "unreachable"

        return [
            HealthResult(
                check_id=f"CHK-{uuid4().hex[:10].upper()}",
                asset_id=self.asset_id,
                check_type="NETWORK",
                metric="tcp_response_time",
                value=value,
                unit="ms",
                status=status,
                severity=severity,
                message=message,
                observed_at=timestamp,
                metadata={"host": self.host, "port": self.port},
            )
        ]


class IPCollector:
    def __init__(
        self,
        asset_id: str,
        target: str,
        timeout_seconds: float = 2.0,
    ):
        if not target or not target.strip():
            raise ValueError("IP address must not be empty")

        timeout_seconds = float(timeout_seconds)

        if timeout_seconds <= 0:
            raise ValueError("Timeout must be greater than zero")

        try:
            self.target = str(ipaddress.ip_address(target.strip()))
        except ValueError as error:
            raise ValueError("Target must be a valid IPv4 or IPv6 address") from error

        self.asset_id = asset_id
        self.timeout_seconds = timeout_seconds

    def collect(self, observed_at: datetime | None = None) -> list[HealthResult]:
        timestamp = observed_at or utc_now()
        address = ipaddress.ip_address(self.target)

        if platform.system() == "Windows":
            command = [
                "ping", "-n", "1", "-w",
                str(max(1, int(self.timeout_seconds * 1000))),
                self.target,
            ]
        else:
            command = [
                "ping", "-c", "1", "-W",
                str(max(1, int(self.timeout_seconds))),
                self.target,
            ]

        try:
            response = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds + 1,
                check=False,
            )

            if response.returncode == 0:
                status = CheckStatus.HEALTHY
                severity = Severity.INFO
                value = "reachable"
                message = f"IP address {self.target} is reachable"
            else:
                status = CheckStatus.CRITICAL
                severity = Severity.CRITICAL
                value = "unreachable"
                message = f"IP address {self.target} is not reachable"

        except subprocess.TimeoutExpired:
            status = CheckStatus.CRITICAL
            severity = Severity.CRITICAL
            value = "unreachable"
            message = f"Ping timed out for {self.target}"

        except FileNotFoundError:
            status = CheckStatus.UNKNOWN
            severity = Severity.MEDIUM
            value = "unknown"
            message = "Ping utility is not installed or unavailable"

        return [
            HealthResult(
                check_id=f"CHK-{uuid4().hex[:10].upper()}",
                asset_id=self.asset_id,
                check_type="NETWORK",
                metric="ip_reachability",
                value=value,
                unit="state",
                status=status,
                severity=severity,
                message=message,
                observed_at=timestamp,
                metadata={
                    "ip_address": self.target,
                    "ip_version": address.version,
                    "protocol": "ICMP",
                },
            )
        ]

class NetworkInterfaceCollector:
    def __init__(
        self,
        asset_id: str,
        interface_names: list[str] | None = None,
    ):
        self.asset_id = asset_id
        self.interface_names = (
            set(interface_names)
            if interface_names is not None
            else None
        )

    def collect(
        self,
        observed_at: datetime | None = None,
    ) -> list[HealthResult]:
        timestamp = observed_at or utc_now()
        results = []

        interfaces = psutil.net_if_addrs()
        interface_stats = psutil.net_if_stats()

        for interface_name, addresses in interfaces.items():

            # Skip interfaces that are not in the configured allowlist.
            if (
                self.interface_names is not None
                and interface_name not in self.interface_names
            ):
                continue

            mac_address = None
            ip_addresses = []

            for address in addresses:
                if address.family == getattr(psutil, "AF_LINK", None):
                    mac_address = address.address
                elif address.family in (socket.AF_INET, socket.AF_INET6):
                    ip_addresses.append(address.address.split("%")[0])

            stats = interface_stats.get(interface_name)
            is_up = bool(stats and stats.isup)

            results.append(
                HealthResult(
                    check_id=f"CHK-{uuid4().hex[:10].upper()}",
                    asset_id=self.asset_id,
                    check_type="NETWORK",
                    metric="network_interface",
                    value="up" if is_up else "down",
                    unit="state",
                    status=(
                        CheckStatus.HEALTHY
                        if is_up
                        else CheckStatus.WARNING
                    ),
                    severity=(
                        Severity.INFO
                        if is_up
                        else Severity.LOW
                    ),
                    message=(
                        f"Network interface {interface_name} is "
                        f"{'up' if is_up else 'down'}"
                    ),
                    observed_at=timestamp,
                    metadata={
                        "interface": interface_name,
                        "mac_address": mac_address,
                        "ip_addresses": ip_addresses,
                        "is_up": is_up,
                        "speed_mbps": stats.speed if stats else None,
                    },
                )
            )

        return results

class DNSCollector:
    def __init__(self, asset_id: str, hostname: str):
        if not hostname or not hostname.strip():
            raise ValueError("Hostname must not be empty")

        self.asset_id = asset_id
        self.hostname = hostname.strip()

    def collect(
        self,
        observed_at: datetime | None = None,
    ) -> list[HealthResult]:
        timestamp = observed_at or utc_now()

        try:
            addresses = socket.getaddrinfo(
                self.hostname,
                None,
                type=socket.SOCK_STREAM,
            )

            resolved_addresses = sorted(
                {item[4][0] for item in addresses}
            )

            status = CheckStatus.HEALTHY
            severity = Severity.INFO
            value = "resolved"
            message = (
                f"DNS resolution succeeded for {self.hostname}: "
                f"{', '.join(resolved_addresses)}"
            )

        except socket.gaierror as error:
            resolved_addresses = []
            status = CheckStatus.CRITICAL
            severity = Severity.CRITICAL
            value = "unresolved"
            message = f"DNS resolution failed for {self.hostname}: {error}"

        return [
            HealthResult(
                check_id=f"CHK-{uuid4().hex[:10].upper()}",
                asset_id=self.asset_id,
                check_type="NETWORK",
                metric="dns_resolution",
                value=value,
                unit="state",
                status=status,
                severity=severity,
                message=message,
                observed_at=timestamp,
                metadata={
                    "hostname": self.hostname,
                    "resolved_addresses": resolved_addresses,
                    "record_count": len(resolved_addresses),
                },
            )
        ]
