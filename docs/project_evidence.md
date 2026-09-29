# Verified Project Evidence

Validation was completed on 29 September 2026 using Python 3.12 on Linux. The same automated workflow is configured for Python 3.10 and 3.12 in GitHub Actions.

## Automated quality results

| Check | Verified result |
|---|---:|
| Pytest tests | 28 passed |
| Python statement coverage | 95% |
| Ruff lint and formatting | Passed |
| Real local monitoring cycle | 4 checks completed successfully |
| Linux Bash health script | Valid JSON with CPU, memory, and disk readings |

The PowerShell script is provided for Windows Server collection. It was syntax-reviewed but cannot be executed in the Linux validation environment; run it on Windows before claiming execution evidence.

## Deterministic demo results

| Metric | Result |
|---|---:|
| CMDB assets | 7 |
| Health checks | 96 |
| Healthy checks | 73 |
| Warning checks | 13 |
| Critical checks | 10 |
| Correlated incidents | 8 |
| Resolved incidents | 8 |
| Incidents with SLA escalation | 6 |
| Incident lifecycle events | 41 |
| Power BI-ready datasets | 6 |

The demo deliberately includes both within-SLA recoveries and breached-SLA escalations. All failures recover by the final cycle, proving incident closure as well as creation.

## Reproduce the evidence

```bash
python -m pip install -e ".[dev,visualization]"
ruff check src tests scripts
pytest --cov=infra_monitor --cov-report=term-missing
python -m infra_monitor --config config/config.example.yaml demo --cycles 12 --reset
python scripts/build_dashboard.py
```

## Resume-ready wording

- Built a lab-based infrastructure monitoring solution using Python, PowerShell, Bash, SQLite, and Power BI-ready datasets to track server, database, network, cloud, VMware, and scheduled-job health.
- Automated threshold-based alert classification, incident correlation, severity-driven SLA escalation, recovery detection, and auditable resolution tracking across 96 deterministic health checks.
- Modeled seven CMDB assets and developed operational dashboards, SQL queries, daily/SLA reports, runbooks, and CI-tested workflows with 28 automated tests and 95% statement coverage.

Keep the phrase **lab-based** on a resume unless the solution has actually been deployed in an enterprise environment.

