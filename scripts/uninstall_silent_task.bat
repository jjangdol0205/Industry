@echo off
setlocal
title TrendPulse - Uninstall Silent Background Sync Task

echo =======================================================
echo  Uninstalling TrendPulse Silent Background Sync Task
echo =======================================================

set "TASK_NAME=TrendPulse_Stock_Sync"
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TrendPulse_Stock_Sync.lnk"

echo [1/2] Deleting Windows Scheduled Task (%TASK_NAME%)...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Scheduled task removed successfully.
) else (
    echo Task '%TASK_NAME%' not found or already removed.
)

echo [2/2] Removing Startup folder fallback shortcut...
if exist "%SHORTCUT_PATH%" (
    del /f /q "%SHORTCUT_PATH%" >nul 2>&1
    echo Startup shortcut removed.
) else (
    echo Startup shortcut not found.
)

echo.
echo =======================================================
echo  Uninstallation Complete!
echo =======================================================
