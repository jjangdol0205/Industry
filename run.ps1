# TrendPulse AI - One-Click Launcher Script (redirection and encoding safe)
$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   TrendPulse AI: Industry Insight Analyzer" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python version
Write-Host "[1/4] Checking Python environment..." -ForegroundColor Yellow
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
Write-Host "[2/4] Setting up Python virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Creating a new one (this may take a minute)..." -ForegroundColor DarkYellow
    & python -m venv .venv
    Write-Host "Virtual environment created successfully!" -ForegroundColor Green
} else {
    Write-Host "Existing virtual environment (.venv) detected." -ForegroundColor Green
}

# 3. Activate and Install dependencies
Write-Host ""
Write-Host "[3/4] Installing required library dependencies..." -ForegroundColor Yellow
# Two-parameter Join-Path is fully compatible with older PowerShell 5.1 / 4.0
$activateScript = Join-Path ".venv" "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    . $activateScript
} else {
    Write-Host "Warning: Activation script not found. Trying global pip installation." -ForegroundColor Red
}

Write-Host "Upgrading pip and installing requirements..." -ForegroundColor DarkYellow
& pip install --upgrade pip
& pip install -r requirements.txt
Write-Host "All library dependencies installed successfully!" -ForegroundColor Green

# 4. Launch FastAPI
Write-Host ""
Write-Host "[4/4] Starting TrendPulse AI Web Server..." -ForegroundColor Yellow
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

# Run Uvicorn
& uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
