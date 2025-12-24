$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = $env:PYTHON_BIN
if ([string]::IsNullOrWhiteSpace($python)) { $python = "python" }
$logDir = Join-Path $projectDir "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$retention = $env:DB_BACKUP_RETENTION
if ([string]::IsNullOrWhiteSpace($retention)) { $retention = 14 }
Set-Location $projectDir
& $python manage.py backup_database --retention-days $retention >> (Join-Path $logDir "backup_database.log") 2>&1

