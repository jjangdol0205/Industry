@echo off
REM ============================================================================
REM Quantitative Turnaround Strategy System - Streamlit Dashboard Launcher
REM Starts Streamlit web application in local browser
REM ============================================================================

setlocal
cd /d "%~dp0"

echo [Quant Turnaround Strategy] Starting Streamlit Interactive Dashboard...

REM Detect Python executable
if exist "..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=..\.venv\Scripts\python.exe"
) else if exist "D:\Industry\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=D:\Industry\.venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [Quant Turnaround Strategy] Using Python: %PYTHON_EXE%
"%PYTHON_EXE%" -m streamlit run app.py --server.port=8501 --server.headless=false

if errorlevel 1 (
    echo [ERROR] Streamlit exited with an error.
    pause
)

endlocal
