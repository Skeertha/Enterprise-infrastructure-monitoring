from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from uuid import uuid4

from infra_monitor.models import CheckStatus, HealthResult, Severity, utc_now


class CloudCLICollector:
    """Read active alerts through an already-authenticated AWS or Azure CLI."""

    def __init__(self, provider: str, asset_id: str, timeout_seconds: int = 20):
        provider = provider.lower()
        if provider not in {"aws", "azure"}:
            raise ValueError("provider must be 'aws' or 'azure'")
        self.provider = provider
        self.asset_id = asset_id
        self.timeout_seconds = timeout_seconds

    def _command(self) -> tuple[str, list[str]]:
        if self.provider == "aws":
            return "aws", [
                "aws",
                "cloudwatch",
                "describe-alarms",
                "--state-value",
                "ALARM",
                "--output",
                "json",
            ]
        return "az", [
            "az",
            "monitor",
            "metrics",
            "alert",
            "list",
            "--output",
            "json",
        ]

    def collect(self, observed_at: datetime | None = None) -> list[HealthResult]:
        timestamp = observed_at or utc_now()
        executable, command = self._command()
        status, severity = CheckStatus.UNKNOWN, Severity.LOW
        value: int | str = "unknown"

        if shutil.which(executable) is None:
            message = f"{executable} CLI is not installed; {self.provider} check skipped"
        else:
            try:
                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
                if process.returncode != 0:
                    raise RuntimeError(process.stderr.strip() or "CLI command failed")
                payload = json.loads(process.stdout or "{}")
                if self.provider == "aws":
                    active = len(payload.get("MetricAlarms", [])) + len(
                        payload.get("CompositeAlarms", [])
                    )
                else:
                    active = len([item for item in payload if item.get("enabled", True)])
                value = active
                if active:
                    status, severity = CheckStatus.WARNING, Severity.HIGH
                    message = f"{active} active {self.provider.upper()} monitoring alert(s)"
                else:
                    status, severity = CheckStatus.HEALTHY, Severity.INFO
                    message = f"No active {self.provider.upper()} monitoring alerts"
            except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
                status, severity = CheckStatus.CRITICAL, Severity.HIGH
                message = f"{self.provider.upper()} monitoring query failed: {error}"

        return [
            HealthResult(
                check_id=f"CHK-{uuid4().hex[:10].upper()}",
                asset_id=self.asset_id,
                check_type="CLOUD",
                metric="active_cloud_alerts",
                value=value,
                unit="alerts",
                status=status,
                severity=severity,
                message=message,
                observed_at=timestamp,
                metadata={"provider": self.provider},
            )
        ]
