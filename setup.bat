@echo off
echo ==========================================================
echo   Kanini Resume Builder — First-Time Setup
echo ==========================================================
echo.

REM ── Backend ──────────────────────────────────────────────────────────
echo [1/3] Setting up Python virtual environment...
cd /d "%~dp0backend"
py -m venv venv
echo [2/3] Installing Python dependencies...
venv\Scripts\pip install -r requirements.txt

REM ── Frontend ─────────────────────────────────────────────────────────
echo [3/3] Installing Node.js dependencies...
cd /d "%~dp0frontend-ng"
call npm install

echo.
echo ==========================================================
echo   Setup complete! Run start.bat to launch the app.
echo ==========================================================
pause
