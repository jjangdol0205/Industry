# TrendPulse AI - One-Click Launcher Script (redirection and encoding safe)
$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   TrendPulse AI: Industry Insight Analyzer" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python version
Write-Host "[1/5] Checking Python environment..." -ForegroundColor Yellow
try {
    $pythonVer = & python --version
    Write-Host "Detected Python: $pythonVer" -ForegroundColor Green
} catch {
    Write-Host "Error: Python is not installed or not added to your system PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from python.org and try again." -ForegroundColor Yellow
    Exit
}

# 2. Virtual Environment setup
Write-Host ""
Write-Host "[2/5] Setting up Python virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Creating a new one (this may take a minute)..." -ForegroundColor DarkYellow
    & python -m venv .venv
    Write-Host "Virtual environment created successfully!" -ForegroundColor Green
} else {
    Write-Host "Existing virtual environment (.venv) detected." -ForegroundColor Green
}

# 3. Activate and verify dependencies (eliminate redundant pip loops)
Write-Host ""
Write-Host "[3/5] Checking required library dependencies..." -ForegroundColor Yellow
$activateScript = Join-Path ".venv" "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    . $activateScript
} else {
    Write-Host "Warning: Activation script not found. Trying global python environment." -ForegroundColor Red
}

$depMarker = Join-Path ".venv" ".installed"
if (-not (Test-Path $depMarker)) {
    Write-Host "First-time setup: Installing required dependencies from requirements.txt..." -ForegroundColor DarkYellow
    & pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        New-Item -ItemType File -Path $depMarker -Force | Out-Null
        Write-Host "All library dependencies installed successfully!" -ForegroundColor Green
    } else {
        Write-Host "Warning: Pip install reported errors; proceeding anyway." -ForegroundColor Yellow
    }
} else {
    Write-Host "Dependencies already installed and up-to-date (skipped redundant pip check)." -ForegroundColor Green
}

# 4. Pre-run Stock Price & Universe Synchronization Hook
Write-Host ""
Write-Host "[4/5] Synchronizing stock prices & 4-tier universe..." -ForegroundColor Yellow
try {
    $pythonExe = Join-Path ".venv" "Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) {
        $pythonExe = "python"
    }
    # Invoke pre-run sync. If cached, completes in <0.2s; if uncached, refreshes; if offline, recovers gracefully.
    & $pythonExe sync_stocks.py --source run.bat
} catch {
    Write-Host "Warning: Pre-run stock sync encountered an issue: $_" -ForegroundColor DarkYellow
    Write-Host "Proceeding with current database state..." -ForegroundColor DarkYellow
}

# 5. Launch Authoritative FastAPI Web Server
Write-Host ""
Write-Host "[5/5] Starting TrendPulse AI Web Server..." -ForegroundColor Yellow
Write-Host "Server successfully started! Please access the following URL in your browser:" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------" -ForegroundColor Green
Write-Host " ===  http://localhost:8000  === " -ForegroundColor Cyan
Write-Host "--------------------------------------------------------" -ForegroundColor Green
Write-Host "To stop the server, press Ctrl + C in this terminal window." -ForegroundColor DarkGray
Write-Host ""

# Open browser automatically if possible
try {
    Start-Process "http://localhost:8000"
} catch {
    Write-Host "Please open http://localhost:8000 manually in your browser." -ForegroundColor Yellow
}

# Run Uvicorn targeting InvestmentPortal backend (which serves API and mounts pre-built React frontend at /)
& uvicorn InvestmentPortal.backend.main:app --host 127.0.0.1 --port 8000
