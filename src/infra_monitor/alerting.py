from __future__ import annotations

from dataclasses import dataclass

from infra_monitor.models import CheckStatus, Severity


@dataclass(frozen=True)
class Threshold:
    warning: float
    critical: float
    direction: str = "high"


def classify_numeric(value: float, threshold: Threshold) -> tuple[CheckStatus, Severity]:
    """Classify a value using high-is-bad or low-is-bad thresholds."""
    if threshold.direction == "high":
        if value >= threshold.critical:
            return CheckStatus.CRITICAL, Severity.CRITICAL
        if value >= threshold.warning:
            return CheckStatus.WARNING, Severity.HIGH
    elif threshold.direction == "low":
        if value <= threshold.critical:
            return CheckStatus.CRITICAL, Severity.CRITICAL
        if value <= threshold.warning:
            return CheckStatus.WARNING, Severity.HIGH
    else:
        raise ValueError("Threshold direction must be 'high' or 'low'")
    return CheckStatus.HEALTHY, Severity.INFO


def threshold_from_config(
    thresholds: dict[str, dict[str, float | str]],
    metric: str,
    default: Threshold,
) -> Threshold:
    values = thresholds.get(metric, {})
    return Threshold(
        warning=float(values.get("warning", default.warning)),
        critical=float(values.get("critical", default.critical)),
        direction=str(values.get("direction", default.direction)),
    )
