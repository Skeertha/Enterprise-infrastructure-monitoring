# Operational Runbook

## Start-of-shift checks

1. Run one monitoring cycle.
2. Review critical and high incidents first.
3. Confirm the monitoring database and export directory are writable.
4. Check scheduled-job heartbeats and database availability.
5. Export and review the latest operational summary.

```bash
infra-monitor --config config/config.example.yaml monitor --cycles 1
infra-monitor --config config/config.example.yaml incidents
infra-monitor --config config/config.example.yaml export
```

## CPU or memory alert

1. Confirm the metric is still above its configured threshold.
2. Identify the highest-consuming process with Task Manager, Resource Monitor, `Get-Process`, `top`, or `ps`.
3. Check for a deployment, backup, scan, or scheduled job at the same time.
4. Do not terminate a process without an approved change or runbook instruction.
5. Escalate with utilization, duration, process evidence, and business impact.

## Disk-space alert

1. Validate usage with `Get-Volume` on Windows or `df -h` on Linux.
2. Locate growth with an approved disk-analysis command or tool.
3. Check logs, temporary files, backups, and database files.
4. Remove or archive data only under an approved retention procedure.
5. Re-run the health check and record the recovered percentage.

## Database-unavailable alert

1. Confirm network path, port, service status, and credentials separately.
2. Run a minimal read-only query such as `SELECT 1`.
3. Review database and operating-system logs around the alert time.
4. Check connection limits, disk space, and scheduled maintenance.
5. Escalate to the database owner with the exact error and timestamp.

## Scheduled-job alert

1. Confirm the last successful heartbeat and expected schedule.
2. Review scheduler history and the job log.
3. Check upstream file, database, credential, and disk dependencies.
4. Re-run only when the job owner confirms it is safe and idempotent.
5. Record the new completion time and validate downstream output.

## Network-endpoint alert

1. Validate DNS resolution.
2. Test the configured TCP port from the monitoring host.
3. Compare latency with its recent baseline.
4. Check firewall changes and provider status.
5. Escalate with source, destination, port, timestamps, and error text.

## Handoff template

```text
Incident:
Business impact:
First detected:
Current state:
Checks completed:
Evidence:
Actions taken:
Owner/escalation group:
Next action and due time:
```

