@echo off
echo ==========================================================
echo   Kanini Resume Builder — First-Time Setup
echo ==========================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
	echo [ERROR] Python 3.10 or later is required. Install it from https://www.python.org/downloads/
	pause
	exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
	echo [ERROR] Node.js 20 LTS or later is required. Install it from https://nodejs.org/
	pause
	exit /b 1
)

REM ── Backend ──────────────────────────────────────────────────────────
echo [1/3] Setting up Python virtual environment...
cd /d "%~dp0backend"
py -m venv venv
if errorlevel 1 (
	echo [ERROR] Could not create the Python virtual environment.
	pause
	exit /b 1
)

echo [2/3] Installing Python dependencies...
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
	echo [ERROR] Could not install Python dependencies. Check your internet connection and Python installation.
	pause
	exit /b 1
)

REM ── Frontend ─────────────────────────────────────────────────────────
echo [3/3] Installing Node.js dependencies...
cd /d "%~dp0frontend-ng"
call npm install
if errorlevel 1 (
	echo [ERROR] Could not install Node.js dependencies. Check your internet connection and Node.js installation.
	pause
	exit /b 1
)

echo.
echo ==========================================================
echo   Setup complete! Run start.bat to launch the app.
echo ==========================================================
pause
