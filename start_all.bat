@echo off
title Ideogram 4 Local Studio Launcher

echo Starting Ideogram 4 Backend API...
start /B "" "C:\ProgramData\miniconda3\envs\comfy_env\python.exe" -m uvicorn backend.app:app --host 127.0.0.1 --port 8000

echo Waiting for API backend to boot...
timeout /t 5 /nobreak > nul

echo Launching Ideogram Studio Control Room in your default browser...
start http://127.0.0.1:8000/frontend/ideogram-studio.html

echo Backend running. Close this command window to shut down the server.
pause
