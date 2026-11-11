@echo off
title YouTube Studio Automator
echo Starting YouTube Studio Automator Desktop Application...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with an error.
    pause
)
