@echo off
setlocal enabledelayedexpansion
title TrendPulse - Install Silent Background Sync Task

echo =======================================================
echo  Installing TrendPulse Silent Background Sync Task
echo =======================================================

:: Resolve script directory and project root
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..") do set "PROJECT_DIR=%%~fI"

set "VBS_PATH=%SCRIPT_DIR%\run_sync_silent.vbs"
set "TASK_NAME=TrendPulse_Stock_Sync"
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TrendPulse_Stock_Sync.lnk"

echo [1/2] Registering Windows Scheduled Task (%TASK_NAME%)...
schtasks /create /tn "%TASK_NAME%" /tr "wscript.exe \"%VBS_PATH%\"" /sc onlogon /rl limited /f

if %ERRORLEVEL% equ 0 (
    echo Scheduled task registered successfully!
) else (
    echo Warning: Task Scheduler registration returned code %ERRORLEVEL%.
)

echo [2/2] Creating Startup folder fallback shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$wsh = New-Object -ComObject WScript.Shell; $sc = $wsh.CreateShortcut('%SHORTCUT_PATH%'); $sc.TargetPath = 'wscript.exe'; $sc.Arguments = '\"%VBS_PATH%\"'; $sc.WorkingDirectory = '%PROJECT_DIR%'; $sc.Description = 'TrendPulse Silent Stock Sync'; $sc.Save()"

if exist "%SHORTCUT_PATH%" (
    echo Startup shortcut created at: %SHORTCUT_PATH%
) else (
    echo Warning: Could not create startup shortcut.
)

echo.
echo =======================================================
echo  Installation Complete!
echo  Stock sync will run silently on Windows logon.
echo =======================================================
