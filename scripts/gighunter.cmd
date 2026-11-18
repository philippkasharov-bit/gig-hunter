@echo off
rem gig-hunter launcher for Windows autostart (Startup folder shortcut).
rem Runs from the repo root so config.yaml, .env and data\ resolve; logs to data\gighunter.log.
rem Restarts after a crash; close the window to stop.
title gig-hunter
cd /d "%~dp0.."
if not exist data mkdir data
set PYTHONUTF8=1
set RESTART_DELAY_S=60
:loop
".venv\Scripts\python.exe" -m gighunter >> data\gighunter.log 2>&1
echo %date% %time% gighunter exited with code %errorlevel%, restarting in %RESTART_DELAY_S%s >> data\gighunter.log
timeout /t %RESTART_DELAY_S% /nobreak >nul
goto loop
