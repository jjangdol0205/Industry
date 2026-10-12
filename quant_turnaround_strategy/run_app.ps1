# ==============================================================================
# Quantitative Turnaround Strategy System - PowerShell Launcher
# Starts Streamlit Interactive Web Dashboard
# ==============================================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  Quantitative Turnaround Strategy System: Web Dashboard Launcher" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Locate Python
$PythonExe = $null
$CandidatePaths = @(
    (Join-Path $ScriptDir "..\.venv\Scripts\python.exe"),
    "D:\Industry\.venv\Scripts\python.exe",
    (Join-Path $ScriptDir ".venv\Scripts\python.exe")
)

foreach ($path in $CandidatePaths) {
    if (Test-Path $path) {
        $PythonExe = (Resolve-Path $path).Path
        break
    }
}

if (-not $PythonExe) {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonExe = $PythonCmd.Source
    } else {
        Write-Error "Could not locate Python executable in .venv or system PATH."
        exit 1
    }
}

Write-Host "Using Python: $PythonExe" -ForegroundColor Green
Write-Host "Launching Streamlit Dashboard (http://localhost:8501)..." -ForegroundColor Yellow

& $PythonExe -m streamlit run (Join-Path $ScriptDir "app.py") --server.port=8501 --server.headless=false
