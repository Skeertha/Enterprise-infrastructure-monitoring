from __future__ import annotations

import ssl
from datetime import datetime
from uuid import uuid4

from infra_monitor.models import CheckStatus, HealthResult, Severity, utc_now


class VMwareCollector:
    """Optional vCenter collector. Requires the `vmware` project extra."""

    def __init__(
        self,
        asset_id: str,
        host: str,
        username: str,
        password: str,
        port: int = 443,
        verify_ssl: bool = True,
    ):
        self.asset_id = asset_id
        self.host = host
        self.username = username
        self.password = password
        self.port = int(port)
        self.verify_ssl = verify_ssl

    def collect(self, observed_at: datetime | None = None) -> list[HealthResult]:
        timestamp = observed_at or utc_now()
        service_instance = None
        try:
            from pyVim.connect import Disconnect, SmartConnect  # type: ignore[import-not-found]
            from pyVmomi import vim  # type: ignore[import-not-found]

            context = ssl.create_default_context()
            if not self.verify_ssl:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            service_instance = SmartConnect(
                host=self.host,
                user=self.username,
                pwd=self.password,
                port=self.port,
                sslContext=context,
            )
            content = service_instance.RetrieveContent()
            view = content.viewManager.CreateContainerView(
                content.rootFolder, [vim.HostSystem], True
            )
            try:
                hosts = list(view.view)
            finally:
                view.Destroy()
            unhealthy = [host.name for host in hosts if str(host.overallStatus) != "green"]
            if unhealthy:
                status, severity = CheckStatus.WARNING, Severity.HIGH
                message = f"{len(unhealthy)} VMware host(s) are not green: {', '.join(unhealthy)}"
            else:
                status, severity = CheckStatus.HEALTHY, Severity.INFO
                message = f"All {len(hosts)} VMware host(s) report green status"
            value: int | str = len(unhealthy)
        except ImportError:
            status, severity = CheckStatus.UNKNOWN, Severity.LOW
            message = "pyVmomi is not installed; VMware check skipped"
            value = "unknown"
        except Exception as error:  # SDK exposes several environment-specific exceptions.
            status, severity = CheckStatus.CRITICAL, Severity.HIGH
            message = f"VMware health query failed: {error}"
            value = "unavailable"
        finally:
            if service_instance is not None:
                Disconnect(service_instance)

        return [
            HealthResult(
                check_id=f"CHK-{uuid4().hex[:10].upper()}",
                asset_id=self.asset_id,
                check_type="VMWARE",
                metric="unhealthy_hosts",
                value=value,
                unit="hosts",
                status=status,
                severity=severity,
                message=message,
                observed_at=timestamp,
                metadata={"vcenter": self.host},
            )
        ]
