$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = $env:PYTHON_BIN
if ([string]::IsNullOrWhiteSpace($python)) { $python = "python" }
$logDir = Join-Path $projectDir "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Set-Location $projectDir
& $python manage.py monitor_pipelines --lookback-minutes 180 >> (Join-Path $logDir "pipelines_health.log") 2>&1

