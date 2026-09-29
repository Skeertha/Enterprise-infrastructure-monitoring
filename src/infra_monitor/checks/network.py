from __future__ import annotations

import socket
import time
from datetime import datetime
from uuid import uuid4

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
        self.asset_id = asset_id
        self.host = host
        self.port = int(port)
        self.timeout_seconds = float(timeout_seconds)
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
