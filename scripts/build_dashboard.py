from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "powerbi" / "data"
OUTPUT = ROOT / "docs" / "images" / "sample_operations_dashboard.png"


def read_rows(filename: str) -> list[dict[str, str]]:
    with (DATA / filename).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def add_card(axis, title: str, value: str, color: str) -> None:
    axis.set_facecolor("#FFFFFF")
    axis.text(0.05, 0.72, title, fontsize=10, color="#64748B", transform=axis.transAxes)
    axis.text(
        0.05, 0.20, value, fontsize=24, fontweight="bold", color=color, transform=axis.transAxes
    )
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_color("#E2E8F0")


def main() -> None:
    checks = read_rows("health_checks.csv")
    incidents = read_rows("incidents.csv")
    status_counts = Counter(row["status"] for row in checks)
    severity_counts = Counter(row["severity"] for row in incidents)
    event_counts = Counter(row["check_type"] for row in checks if row["status"] != "HEALTHY")

    health_percentage = 100 * status_counts.get("HEALTHY", 0) / max(1, len(checks))
    active = sum(row["status"] != "RESOLVED" for row in incidents)
    breached = sum(int(row["escalation_level"]) > 0 for row in incidents)
    resolution_values = [
        float(row["resolution_minutes"]) for row in incidents if row.get("resolution_minutes")
    ]
    mttr = sum(resolution_values) / max(1, len(resolution_values))

    figure = plt.figure(figsize=(14, 8), facecolor="#F1F5F9")
    grid = figure.add_gridspec(3, 4, height_ratios=[0.8, 2.2, 2.2], hspace=0.42, wspace=0.32)
    add_card(figure.add_subplot(grid[0, 0]), "TOTAL CHECKS", f"{len(checks):,}", "#2563EB")
    add_card(figure.add_subplot(grid[0, 1]), "HEALTHY", f"{health_percentage:.1f}%", "#16A34A")
    add_card(figure.add_subplot(grid[0, 2]), "ACTIVE INCIDENTS", str(active), "#DC2626")
    add_card(figure.add_subplot(grid[0, 3]), "MTTR", f"{mttr:.0f} min", "#7C3AED")

    status_axis = figure.add_subplot(grid[1, :2])
    status_names = ["HEALTHY", "WARNING", "CRITICAL"]
    status_axis.bar(
        status_names,
        [status_counts.get(name, 0) for name in status_names],
        color=["#16A34A", "#F59E0B", "#DC2626"],
    )
    status_axis.set_title("Health Checks by Status", loc="left", fontweight="bold")
    status_axis.set_ylabel("Checks")
    status_axis.grid(axis="y", alpha=0.2)

    severity_axis = figure.add_subplot(grid[1, 2:])
    severity_names = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    severity_axis.barh(
        severity_names,
        [severity_counts.get(name, 0) for name in severity_names],
        color=["#991B1B", "#DC2626", "#F59E0B", "#2563EB"],
    )
    severity_axis.set_title("Incidents by Severity", loc="left", fontweight="bold")
    severity_axis.set_xlabel("Incidents")
    severity_axis.grid(axis="x", alpha=0.2)

    type_axis = figure.add_subplot(grid[2, :3])
    types = [name for name, _ in event_counts.most_common()]
    values = [event_counts[name] for name in types]
    type_axis.bar(types, values, color="#2563EB")
    type_axis.set_title("Non-Healthy Checks by Monitoring Domain", loc="left", fontweight="bold")
    type_axis.set_ylabel("Checks")
    type_axis.tick_params(axis="x", rotation=20)
    type_axis.grid(axis="y", alpha=0.2)

    sla_axis = figure.add_subplot(grid[2, 3])
    within = max(0, len(incidents) - breached)
    sla_axis.pie(
        [within, breached],
        labels=["Within SLA", "Breached"],
        colors=["#16A34A", "#DC2626"],
        autopct="%1.0f%%",
        startangle=90,
    )
    sla_axis.set_title("SLA Outcome", loc="left", fontweight="bold")

    figure.suptitle(
        "Enterprise Infrastructure Operations Dashboard",
        x=0.03,
        y=0.98,
        ha="left",
        fontsize=18,
        fontweight="bold",
        color="#0F172A",
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT, dpi=160, bbox_inches="tight")
    plt.close(figure)
    print(OUTPUT)


if __name__ == "__main__":
    main()
