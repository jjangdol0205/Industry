# TrendPulse - Uninstall Silent Background Sync Task (PowerShell)
$ErrorActionPreference = "Continue"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " Uninstalling TrendPulse Silent Background Sync Task" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

$taskName = "TrendPulse_Stock_Sync"
$startupShortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\TrendPulse_Stock_Sync.lnk"

# 1. Delete scheduled task
Write-Host "[1/2] Deleting Windows Scheduled Task ($taskName)..." -ForegroundColor Yellow
& schtasks.exe /delete /tn $taskName /f 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Scheduled task removed successfully." -ForegroundColor Green
} else {
    Write-Host "Task '$taskName' was not found or already removed." -ForegroundColor Gray
}

# 2. Delete startup shortcut
Write-Host "[2/2] Removing Startup folder fallback shortcut..." -ForegroundColor Yellow
if (Test-Path $startupShortcut) {
    Remove-Item $startupShortcut -Force -ErrorAction SilentlyContinue
    Write-Host "Startup shortcut removed." -ForegroundColor Green
} else {
    Write-Host "Startup shortcut was not found." -ForegroundColor Gray
}

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " Uninstallation Complete!" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
