# TrendPulse - Install Silent Background Sync Task (PowerShell)
$ErrorActionPreference = "Continue"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " Installing TrendPulse Silent Background Sync Task" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$vbsPath = Join-Path $scriptDir "run_sync_silent.vbs"
$taskName = "TrendPulse_Stock_Sync"
$startupShortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\TrendPulse_Stock_Sync.lnk"

# 1. Register Task Scheduler task
Write-Host "[1/2] Registering Windows Scheduled Task ($taskName)..." -ForegroundColor Yellow
$actionArg = "wscript.exe `"$vbsPath`""
& schtasks.exe /create /tn $taskName /tr $actionArg /sc onlogon /rl limited /f

if ($LASTEXITCODE -eq 0) {
    Write-Host "Scheduled task registered successfully!" -ForegroundColor Green
} else {
    Write-Host "Warning: schtasks returned exit code $LASTEXITCODE." -ForegroundColor DarkYellow
}

# 2. Create Startup folder shortcut fallback
Write-Host "[2/2] Creating Startup folder fallback shortcut..." -ForegroundColor Yellow
try {
    $wsh = New-Object -ComObject WScript.Shell
    $sc = $wsh.CreateShortcut($startupShortcut)
    $sc.TargetPath = "wscript.exe"
    $sc.Arguments = "`"$vbsPath`""
    $sc.WorkingDirectory = $projectRoot
    $sc.Description = "TrendPulse Silent Stock Sync"
    $sc.Save()
    Write-Host "Startup shortcut created at: $startupShortcut" -ForegroundColor Green
} catch {
    Write-Host "Warning: Failed to create startup shortcut: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " Installation Complete! Stock sync will run on logon." -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
