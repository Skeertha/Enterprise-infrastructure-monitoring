# Five-Minute Interview Walkthrough

## 1. Problem — 30 seconds

“I built this lab to simulate the daily work of an infrastructure operations team: monitor heterogeneous assets, detect failures, avoid duplicate incidents, track SLA deadlines, document the lifecycle, and create management reporting.”

## 2. Architecture — 60 seconds

Show the README architecture. Explain that every collector returns the same normalized health-result model. Threshold logic assigns status and severity. SQLite keeps CMDB, measurement, incident, and event data. The reporting layer exports a stable model for Power BI.

## 3. Live demo — 90 seconds

```bash
python -m infra_monitor --config config/config.example.yaml demo --reset
python -m infra_monitor --config config/config.example.yaml incidents
```

Point out that the demo is deterministic: high CPU, disk, network latency, database outage, cloud alert, VMware host state, and delayed JDE-style job events appear and then recover. Incidents are correlated instead of duplicated. Virtual time advances by 20 minutes per cycle so SLA escalation can be demonstrated immediately.

## 4. Evidence — 60 seconds

Open the dashboard preview or Power BI report. Show total checks, availability/health percentage, open versus resolved incidents, SLA breaches, severity, and MTTR. Then open `incident_events.csv` to show the audit timeline.

## 5. Engineering quality — 60 seconds

Show the tests and GitHub Actions workflow. Explain that credentials are not committed, integrations are disabled by default, cloud access uses already-authenticated CLIs, and vCenter should use a read-only service account.

## Likely follow-up questions

**Why SQLite?**  
It makes the lab portable. The repository also includes explicit SQL schema and queries, and the storage boundary can be replaced with SQL Server or PostgreSQL.

**How do you prevent alert storms?**  
Active incidents are correlated by asset, check type, and metric. Repeated alerts update the existing incident and add an event.

**What happens when the asset recovers?**  
A healthy result with the same fingerprint auto-resolves the incident and records the recovery event.

**How would you productionize it?**  
Use a central time-series and relational store, a queue between collection and incident processing, secret management, high availability, role-based access, notification integrations, retry/backoff, observability for the monitor itself, and approved ServiceNow/Jira workflows.

**What did you personally implement?**  
Answer only with what you actually ran and can show. The repository clearly distinguishes local checks, deterministic simulation, and credential-dependent integrations.

