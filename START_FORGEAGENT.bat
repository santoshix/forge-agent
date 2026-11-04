@echo off
setlocal
cd /d "%~dp0"
if not exist .venv-forge\Scripts\python.exe (
 echo Run setup_windows.bat first.
 pause
 exit /b 1
)
echo Open http://127.0.0.1:8001 after Application startup complete.
echo Keep this window open. Press Ctrl+C to stop.
.venv-forge\Scripts\python.exe -m uvicorn forge.api:app --host 127.0.0.1 --port 8001
pause
