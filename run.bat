@echo off
setlocal
cd /d "%~dp0"
title YouTube Studio Automator
echo Starting UI and background services...
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    py -3 launcher.py
) else (
    python launcher.py
)
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with an error.
    pause
    exit /b 1
)
