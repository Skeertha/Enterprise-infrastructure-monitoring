# Power BI Build Guide

## Import

Run the demo or export command first. In Power BI Desktop, choose **Get data → Text/CSV** and import all six files from `powerbi/data/`.

Set these data types:

| Table | Column | Type |
|---|---|---|
| assets | asset_id | Text |
| health_checks | observed_at | Date/Time/Timezone |
| health_checks | value | Decimal number when the selected metric is numeric |
| incidents | opened_at, due_at, acknowledged_at, resolved_at | Date/Time/Timezone |
| incidents | resolution_minutes | Decimal number |
| incidents | sla_met | Whole number |
| incident_events | created_at | Date/Time/Timezone |
| daily_status | report_date | Date |

Because `health_checks.value` can also contain `unreachable` or `unknown`, create a numeric Power Query column with `try Number.From([value]) otherwise null` for metric charts.

## Relationships

Create these one-to-many, single-direction relationships:

| One side | Many side | Key |
|---|---|---|
| assets | health_checks | asset_id |
| assets | incidents | asset_id |
| incidents | incident_events | incident_id |

`daily_status` and `sla_summary` are pre-aggregated convenience tables and do not require a relationship.

## Recommended pages

### Operations Overview

- Cards: Total Checks, Health %, Active Incidents, Critical Incidents, SLA Compliance %, MTTR.
- Donut: checks by status.
- Column chart: incidents by severity.
- Line chart: health percentage by date.
- Table: active incidents with asset, severity, due time, and escalation level.

### Infrastructure Health

- Slicers: environment, asset type, hostname, metric, and date.
- Line chart: numeric metric value by observed time.
- Matrix: asset and metric with latest status.
- Bar chart: warning and critical checks by asset.

### Incident & SLA

- Funnel or bar chart: incident status.
- Column chart: average resolution minutes by severity.
- Table: incident event timeline.
- Cards: breached incidents and maximum escalation level.

## Measures and theme

Copy measures from [measures.dax](measures.dax). Import [operations-theme.json](operations-theme.json) through **View → Themes → Browse for themes**.

## Refresh

Run the exporter before refreshing the report:

```bash
infra-monitor --config config/config.example.yaml export
```

For a scheduled refresh in a real environment, store the datasets in an approved shared location or connect Power BI directly to the production database through a governed gateway.

