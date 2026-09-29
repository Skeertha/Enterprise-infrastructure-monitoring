#!/usr/bin/env bash
set -euo pipefail

asset_id="${1:-LOCAL-LNX-01}"
warning="${WARNING_PERCENT:-80}"
critical="${CRITICAL_PERCENT:-90}"

status_for() {
  local value="${1%.*}"
  if (( value >= critical )); then
    printf 'CRITICAL'
  elif (( value >= warning )); then
    printf 'WARNING'
  else
    printf 'HEALTHY'
  fi
}

read -r cpu _ < <(awk '/^cpu / {idle=$5; total=0; for(i=2;i<=NF;i++) total+=$i; printf "%.2f %s\n", 100*(total-idle)/total, "ok"}' /proc/stat)
memory=$(free | awk '/Mem:/ {printf "%.2f", ($3/$2)*100}')
disk=$(df -P / | awk 'NR==2 {gsub("%", "", $5); printf "%.2f", $5}')
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

printf '[\n'
printf '  {"asset_id":"%s","metric":"cpu_percent","value":%s,"unit":"%%","status":"%s","observed_at":"%s"},\n' "$asset_id" "$cpu" "$(status_for "$cpu")" "$timestamp"
printf '  {"asset_id":"%s","metric":"memory_percent","value":%s,"unit":"%%","status":"%s","observed_at":"%s"},\n' "$asset_id" "$memory" "$(status_for "$memory")" "$timestamp"
printf '  {"asset_id":"%s","metric":"disk_percent","value":%s,"unit":"%%","status":"%s","observed_at":"%s"}\n' "$asset_id" "$disk" "$(status_for "$disk")" "$timestamp"
printf ']\n'
