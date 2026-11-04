@echo off
cd /d "%~dp0"
.venv-forge\Scripts\python.exe -m pytest -q
pause
