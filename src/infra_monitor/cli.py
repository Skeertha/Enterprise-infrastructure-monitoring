from __future__ import annotations

import argparse
import sys
import time
from datetime import timedelta
from typing import Any

from infra_monitor.checks.demo import DEMO_ASSETS, DemoCollector
from infra_monitor.config import load_config, project_path
from infra_monitor.incidents import IncidentManager
from infra_monitor.models import CheckStatus, utc_now
from infra_monitor.reporting import PowerBIExporter
from infra_monitor.runner import MonitoringRunner, assets_from_config, build_collectors
from infra_monitor.storage import SQLiteStore


def _runtime(config_path: str) -> tuple[dict[str, Any], SQLiteStore, IncidentManager]:
    config = load_config(config_path)
    database_path = project_path(config, "database_path", "data/monitoring.db")
    store = SQLiteStore(database_path)
    store.initialize()
    manager = IncidentManager(
        store,
        sla_minutes=config.get("sla_minutes", {}),
        auto_resolve=bool(config.get("auto_resolve", True)),
    )
    return config, store, manager


def _print_cycle(cycle: int, results: list[Any], escalated: list[str] | None = None) -> None:
    warning = sum(result.status == CheckStatus.WARNING for result in results)
    critical = sum(result.status == CheckStatus.CRITICAL for result in results)
    healthy = sum(result.status == CheckStatus.HEALTHY for result in results)
    suffix = f", {len(escalated)} escalated" if escalated else ""
    print(f"Cycle {cycle:02d}: {healthy} healthy, {warning} warning, {critical} critical{suffix}")


def command_init(args: argparse.Namespace) -> int:
    config, store, _ = _runtime(args.config)
    store.upsert_assets(assets_from_config(config))
    print(f"Initialized monitoring database: {store.path}")
    return 0


def command_monitor(args: argparse.Namespace) -> int:
    config, store, manager = _runtime(args.config)
    store.upsert_assets(assets_from_config(config))
    collectors = build_collectors(config)
    if not collectors:
        print("No enabled collectors were found in the configuration.", file=sys.stderr)
        return 2
    runner = MonitoringRunner(store, manager, collectors)
    for cycle in range(1, args.cycles + 1):
        results = runner.run_once()
        _print_cycle(cycle, results)
        if cycle < args.cycles and args.interval > 0:
            time.sleep(args.interval)
    return 0


def command_demo(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    database_path = project_path(config, "database_path", "data/monitoring.db")
    if args.reset and database_path.exists():
        database_path.unlink()
    store = SQLiteStore(database_path)
    store.initialize()
    store.upsert_assets(DEMO_ASSETS)
    manager = IncidentManager(store, sla_minutes=config.get("sla_minutes", {}))
    collector = DemoCollector()

    start = utc_now() - timedelta(minutes=max(0, args.cycles - 1) * 20)
    for offset in range(args.cycles):
        observed_at = start + timedelta(minutes=offset * 20)
        results = collector.collect(offset, observed_at)
        for result in results:
            store.record_health_result(result)
            manager.process(result)
        escalated = manager.escalate_due(observed_at)
        _print_cycle(offset + 1, results, escalated)
        if args.interval > 0 and offset + 1 < args.cycles:
            time.sleep(args.interval)

    output_dir = project_path(config, "export_directory", "powerbi/data")
    exported = PowerBIExporter(store, output_dir).export_all()
    print(f"Demo completed. Exported {len(exported)} Power BI dataset files to {output_dir}")
    return 0


def command_export(args: argparse.Namespace) -> int:
    config, store, _ = _runtime(args.config)
    output_dir = project_path(config, "export_directory", "powerbi/data")
    exported = PowerBIExporter(store, output_dir).export_all()
    for path in exported:
        print(path)
    return 0


def command_incidents(args: argparse.Namespace) -> int:
    _, store, _ = _runtime(args.config)
    rows = store.query(
        """
        SELECT incident_id, asset_id, severity, status, opened_at, due_at,
               escalation_level, title
        FROM incidents ORDER BY opened_at DESC
        """
    )
    if not rows:
        print("No incidents found.")
        return 0
    for row in rows:
        print(
            f"{row['incident_id']} | {row['severity']:<8} | {row['status']:<12} | "
            f"{row['asset_id']:<12} | L{row['escalation_level']} | {row['title']}"
        )
    return 0


def command_acknowledge(args: argparse.Namespace) -> int:
    _, _, manager = _runtime(args.config)
    if not manager.acknowledge(args.incident_id):
        print("Incident was not found or is not active.", file=sys.stderr)
        return 1
    print(f"Acknowledged {args.incident_id}")
    return 0


def command_resolve(args: argparse.Namespace) -> int:
    _, _, manager = _runtime(args.config)
    if not manager.resolve(args.incident_id, args.note):
        print("Incident was not found or is not active.", file=sys.stderr)
        return 1
    print(f"Resolved {args.incident_id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infra-monitor",
        description="Enterprise infrastructure monitoring and incident management lab",
    )
    parser.add_argument(
        "--config", default="config/config.example.yaml", help="Path to YAML configuration"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init_parser = commands.add_parser("init-db", help="Initialize the database and CMDB")
    init_parser.set_defaults(handler=command_init)

    monitor_parser = commands.add_parser("monitor", help="Run configured health checks")
    monitor_parser.add_argument("--cycles", type=int, default=1)
    monitor_parser.add_argument("--interval", type=float, default=60)
    monitor_parser.set_defaults(handler=command_monitor)

    demo_parser = commands.add_parser("demo", help="Generate deterministic portfolio data")
    demo_parser.add_argument("--cycles", type=int, default=12)
    demo_parser.add_argument("--interval", type=float, default=0)
    demo_parser.add_argument("--reset", action="store_true")
    demo_parser.set_defaults(handler=command_demo)

    export_parser = commands.add_parser("export", help="Export Power BI-ready CSV files")
    export_parser.set_defaults(handler=command_export)

    incident_parser = commands.add_parser("incidents", help="List incident records")
    incident_parser.set_defaults(handler=command_incidents)

    acknowledge_parser = commands.add_parser("acknowledge", help="Acknowledge an incident")
    acknowledge_parser.add_argument("incident_id")
    acknowledge_parser.set_defaults(handler=command_acknowledge)

    resolve_parser = commands.add_parser("resolve", help="Resolve an incident")
    resolve_parser.add_argument("incident_id")
    resolve_parser.add_argument("--note", required=True, help="Resolution note")
    resolve_parser.set_defaults(handler=command_resolve)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "cycles", 1) < 1:
        raise SystemExit("--cycles must be at least 1")
    return int(args.handler(args))
