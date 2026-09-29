from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from infra_monitor.models import (
    CheckStatus,
    HealthResult,
    Incident,
    Severity,
    as_utc_iso,
    utc_now,
)
from infra_monitor.storage import SQLiteStore

DEFAULT_SLA_MINUTES = {
    Severity.CRITICAL: 15,
    Severity.HIGH: 30,
    Severity.MEDIUM: 120,
    Severity.LOW: 480,
    Severity.INFO: 1440,
}


class IncidentManager:
    def __init__(
        self,
        store: SQLiteStore,
        sla_minutes: dict[str, int] | None = None,
        auto_resolve: bool = True,
    ):
        self.store = store
        configured = {key.upper(): int(value) for key, value in (sla_minutes or {}).items()}
        self.sla_minutes = {
            severity: configured.get(severity.value, default)
            for severity, default in DEFAULT_SLA_MINUTES.items()
        }
        self.auto_resolve = auto_resolve

    @staticmethod
    def fingerprint(result: HealthResult) -> str:
        return f"{result.asset_id}:{result.check_type}:{result.metric}"

    def process(self, result: HealthResult) -> str | None:
        fingerprint = self.fingerprint(result)
        active = self.store.find_active_incident(fingerprint)
        observed_iso = as_utc_iso(result.observed_at)
        assert observed_iso is not None

        if result.status in {CheckStatus.WARNING, CheckStatus.CRITICAL}:
            if active:
                self.store.update_active_incident(
                    active["incident_id"],
                    description=result.message,
                    severity=result.severity.value,
                    updated_at=observed_iso,
                )
                self.store.add_incident_event(
                    active["incident_id"],
                    "REPEATED_ALERT",
                    result.message,
                    observed_iso,
                )
                return str(active["incident_id"])

            incident_id = f"INC-{result.observed_at:%Y%m%d}-{uuid4().hex[:8].upper()}"
            due_at = result.observed_at + timedelta(minutes=self.sla_minutes[result.severity])
            incident = Incident(
                incident_id=incident_id,
                fingerprint=fingerprint,
                check_id=result.check_id,
                asset_id=result.asset_id,
                title=f"{result.metric.replace('_', ' ').title()} alert on {result.asset_id}",
                description=result.message,
                severity=result.severity,
                status="OPEN",
                opened_at=result.observed_at,
                due_at=due_at,
                last_updated_at=result.observed_at,
            )
            self.store.create_incident(incident)
            self.store.add_incident_event(
                incident_id,
                "CREATED",
                f"Incident created with {self.sla_minutes[result.severity]} minute SLA",
                observed_iso,
            )
            return incident_id

        if result.status == CheckStatus.HEALTHY and active and self.auto_resolve:
            self.store.resolve_incident(
                active["incident_id"],
                observed_iso,
                f"Auto-resolved after a healthy check: {result.message}",
            )
            self.store.add_incident_event(
                active["incident_id"],
                "RESOLVED",
                "Monitoring returned to a healthy state",
                observed_iso,
            )
            return str(active["incident_id"])
        return None

    def escalate_due(self, now: datetime | None = None) -> list[str]:
        current = now or utc_now()
        current_iso = as_utc_iso(current)
        assert current_iso is not None
        escalated: list[str] = []
        for incident in self.store.list_due_incidents(current_iso):
            level = int(incident["escalation_level"]) + 1
            severity = Severity(str(incident["severity"]))
            extension = max(15, self.sla_minutes[severity] // 2)
            next_due = current + timedelta(minutes=extension)
            next_due_iso = as_utc_iso(next_due)
            assert next_due_iso is not None
            self.store.escalate_incident(
                str(incident["incident_id"]), level, next_due_iso, current_iso
            )
            self.store.add_incident_event(
                str(incident["incident_id"]),
                "ESCALATED",
                f"SLA breached; escalated to level {level}",
                current_iso,
            )
            escalated.append(str(incident["incident_id"]))
        return escalated

    def acknowledge(self, incident_id: str, now: datetime | None = None) -> bool:
        timestamp = as_utc_iso(now or utc_now())
        assert timestamp is not None
        updated = self.store.acknowledge_incident(incident_id, timestamp)
        if updated:
            self.store.add_incident_event(
                incident_id, "ACKNOWLEDGED", "Incident acknowledged by operator", timestamp
            )
        return updated

    def resolve(
        self,
        incident_id: str,
        resolution: str,
        now: datetime | None = None,
    ) -> bool:
        timestamp = as_utc_iso(now or utc_now())
        assert timestamp is not None
        updated = self.store.manually_resolve_incident(incident_id, timestamp, resolution)
        if updated:
            self.store.add_incident_event(incident_id, "RESOLVED", resolution, timestamp)
        return updated
