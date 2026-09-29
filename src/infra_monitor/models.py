from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


class CheckStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class Asset:
    asset_id: str
    hostname: str
    asset_type: str
    operating_system: str = "Unknown"
    environment: str = "Lab"
    owner: str = "Infrastructure Operations"
    ip_address: str = ""
    location: str = "Lab"
    criticality: str = "Medium"
    status: str = "Active"


@dataclass(frozen=True)
class HealthResult:
    check_id: str
    asset_id: str
    check_type: str
    metric: str
    value: float | int | str | None
    unit: str
    status: CheckStatus
    severity: Severity
    message: str
    observed_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["status"] = self.status.value
        record["severity"] = self.severity.value
        record["observed_at"] = as_utc_iso(self.observed_at)
        record["metadata_json"] = json.dumps(record.pop("metadata"), sort_keys=True)
        return record


@dataclass(frozen=True)
class Incident:
    incident_id: str
    fingerprint: str
    check_id: str
    asset_id: str
    title: str
    description: str
    severity: Severity
    status: str
    opened_at: datetime
    due_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    resolution: str | None = None
    escalation_level: int = 0
    last_updated_at: datetime = field(default_factory=utc_now)
