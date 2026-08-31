@echo off
echo ==========================================================
echo   Kanini Resume Builder — Starting Application
echo ==========================================================
echo.
echo Starting FastAPI backend on http://localhost:8000 ...
start "Kanini Backend" cmd /k "cd /d "%~dp0backend" && venv\Scripts\python main.py"

timeout /t 3 /nobreak >nul

echo Starting Angular frontend on http://localhost:4200 ...
start "Kanini Frontend" cmd /k "cd /d "%~dp0frontend-ng" && npm start"

timeout /t 6 /nobreak >nul
echo.
echo ==========================================================
echo   App is running!
echo   Frontend : http://localhost:4200
echo   API Docs : http://localhost:8000/docs
echo ==========================================================
start "" "http://localhost:4200"
