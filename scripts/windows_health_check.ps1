param(
    [string]$AssetId = "LOCAL-WIN-01",
    [int]$WarningPercent = 80,
    [int]$CriticalPercent = 90
)

$ErrorActionPreference = "Stop"

function Get-Status {
    param([double]$Value)
    if ($Value -ge $CriticalPercent) { return "CRITICAL" }
    if ($Value -ge $WarningPercent) { return "WARNING" }
    return "HEALTHY"
}

$cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
$os = Get-CimInstance Win32_OperatingSystem
$memoryUsed = (($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize) * 100
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$diskUsed = (($disk.Size - $disk.FreeSpace) / $disk.Size) * 100
$timestamp = (Get-Date).ToUniversalTime().ToString("o")

$results = @(
    [PSCustomObject]@{ asset_id=$AssetId; metric="cpu_percent"; value=[math]::Round($cpu,2); unit="%"; status=(Get-Status $cpu); observed_at=$timestamp },
    [PSCustomObject]@{ asset_id=$AssetId; metric="memory_percent"; value=[math]::Round($memoryUsed,2); unit="%"; status=(Get-Status $memoryUsed); observed_at=$timestamp },
    [PSCustomObject]@{ asset_id=$AssetId; metric="disk_percent"; value=[math]::Round($diskUsed,2); unit="%"; status=(Get-Status $diskUsed); observed_at=$timestamp }
)

$results | ConvertTo-Json

