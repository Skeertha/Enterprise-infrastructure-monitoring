# Architecture

## Design goals

The solution is intentionally small enough to run on a laptop while preserving the same separation of concerns used in larger operations platforms: collection, classification, persistence, incident workflow, escalation, and reporting.

```mermaid
flowchart LR
    subgraph Sources
        A["Windows/Linux"]
        B["DB, TCP, jobs"]
        C["Cloud/VMware"]
    end
    D["Collectors"] --> E["Health results"]
    A --> D
    B --> D
    C --> D
    E --> F["Incident manager"]
    E --> G["SQLite"]
    F --> G
    G --> H["CSV / Power BI"]
```

## Components

| Component | Responsibility |
|---|---|
| `checks/` | Collect measurements and normalize them into `HealthResult` records |
| `alerting.py` | Convert numeric measurements into healthy, warning, or critical states |
| `storage.py` | Maintain CMDB, health history, incidents, and lifecycle events in SQLite |
| `incidents.py` | Deduplicate alerts, assign SLAs, escalate breaches, and resolve recoveries |
| `runner.py` | Build configured collectors and execute one monitoring cycle |
| `reporting.py` | Produce a stable CSV contract for Power BI or Excel |
| `cli.py` | Expose initialization, monitoring, demo, incident, and export operations |

## Data model

```mermaid
erDiagram
    ASSETS ||--o{ HEALTH_CHECKS : produces
    ASSETS ||--o{ INCIDENTS : affected_by
    INCIDENTS ||--o{ INCIDENT_EVENTS : records
    ASSETS {
        string asset_id PK
        string hostname
        string asset_type
        string criticality
    }
    HEALTH_CHECKS {
        int id PK
        string asset_id FK
        string metric
        string status
        datetime observed_at
    }
    INCIDENTS {
        string incident_id PK
        string asset_id FK
        string severity
        string status
        datetime due_at
    }
    INCIDENT_EVENTS {
        int id PK
        string incident_id FK
        string event_type
        datetime created_at
    }
```

## Incident correlation

The correlation fingerprint is `asset_id + check_type + metric`. A repeated unhealthy check updates the same active incident instead of opening duplicates. A healthy result with the same fingerprint automatically closes the active incident when `auto_resolve` is enabled.

## Portability

- SQLite avoids requiring a database server for the lab.
- YAML separates thresholds, assets, and collector settings from code.
- `psutil` provides cross-platform host metrics.
- Provider integrations are optional and imported only when enabled.
- CSV is the stable handoff format for Power BI.

