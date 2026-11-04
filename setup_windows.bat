@echo off
setlocal
cd /d "%~dp0"
echo Preparing ForgeAgent with Python 3.12...
py -3.12 --version >nul 2>&1
if errorlevel 1 goto missing
py -3.12 -m venv .venv-forge
if errorlevel 1 goto failed
.venv-forge\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto failed
.venv-forge\Scripts\python.exe -m pip install -r requirements-dev.txt
if errorlevel 1 goto failed
echo.
echo Setup complete. Double-click START_FORGEAGENT.bat next.
pause
exit /b 0
:missing
echo Python 3.12 was not found. Install Python 3.12, then retry.
echo If Python install manager is installed, run: pymanager install 3.12
:failed
echo Setup failed. Copy the error above for troubleshooting.
pause
exit /b 1
