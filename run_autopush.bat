@echo off
title Git Auto-Push Agent - YouTube Automator
cd /d "%~dp0"
echo =======================================================
echo   Git Auto-Push Agent
echo   Whenever you update or save code, it pushes to GitHub!
echo =======================================================
python src\git_autopush.py
pause
