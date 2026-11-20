import pytest

from infra_monitor.alerting import Threshold, classify_numeric
from infra_monitor.models import CheckStatus, Severity


@pytest.mark.parametrize(
    ("value", "expected_status", "expected_severity"),
    [
        (45, CheckStatus.HEALTHY, Severity.INFO),
        (80, CheckStatus.WARNING, Severity.HIGH),
        (95, CheckStatus.CRITICAL, Severity.CRITICAL),
    ],
)
def test_high_is_bad_thresholds(value, expected_status, expected_severity):
    assert classify_numeric(value, Threshold(80, 90)) == (
        expected_status,
        expected_severity,
    )


def test_low_is_bad_thresholds():
    threshold = Threshold(warning=20, critical=10, direction="low")
    assert classify_numeric(30, threshold)[0] == CheckStatus.HEALTHY
    assert classify_numeric(15, threshold)[0] == CheckStatus.WARNING
    assert classify_numeric(5, threshold)[0] == CheckStatus.CRITICAL


def test_invalid_threshold_direction():
    with pytest.raises(ValueError, match="direction"):
        classify_numeric(50, Threshold(80, 90, direction="sideways"))

def test_high_direction_rejects_critical_below_warning():
    with pytest.raises(ValueError, match="[Cc]ritical"):
        Threshold(warning=90, critical=80)

def test_low_direction_rejects_critical_above_warning():
    with pytest.raises(ValueError, match="[Cc]ritical"):
        Threshold(warning=10, critical=20, direction="low")

def test_invalid_direction_rejected_on_creation():
    with pytest.raises(ValueError, match="direction"):
        Threshold(warning=80, critical=90, direction="sideways")