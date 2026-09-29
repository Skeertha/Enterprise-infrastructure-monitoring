-- Active incidents ordered by operational priority
SELECT incident_id, asset_id, severity, status, title, opened_at, due_at,
       escalation_level
FROM incidents
WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'ESCALATED')
ORDER BY CASE severity
    WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
    opened_at;

-- Latest health result for every asset and metric
WITH ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY asset_id, metric ORDER BY observed_at DESC, id DESC
    ) AS row_number
    FROM health_checks
)
SELECT asset_id, check_type, metric, value, unit, status, observed_at
FROM ranked
WHERE row_number = 1
ORDER BY asset_id, metric;

-- SLA and mean time to resolution summary
SELECT severity,
       COUNT(*) AS incidents,
       SUM(CASE WHEN escalation_level = 0 THEN 1 ELSE 0 END) AS within_sla,
       ROUND(AVG(CASE WHEN resolved_at IS NOT NULL
           THEN (julianday(resolved_at) - julianday(opened_at)) * 1440 END), 2)
           AS avg_resolution_minutes
FROM incidents
GROUP BY severity;

