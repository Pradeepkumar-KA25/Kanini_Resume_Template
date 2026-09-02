@echo off
echo ==========================================================
echo   Kanini Resume Builder — Starting Application
echo ==========================================================
echo.

if not exist "%~dp0backend\venv\Scripts\python.exe" (
	echo [ERROR] Setup has not completed. Run setup.bat first.
	pause
	exit /b 1
)

if not exist "%~dp0frontend-ng\node_modules" (
	echo [ERROR] Frontend dependencies are missing. Run setup.bat first.
	pause
	exit /b 1
)

echo Starting FastAPI backend on http://localhost:8000 ...
start "Kanini Backend" cmd /k "cd /d ""%~dp0backend"" && venv\Scripts\python.exe main.py"

timeout /t 3 /nobreak >nul

echo Starting Angular frontend on http://localhost:4200 ...
start "Kanini Frontend" cmd /k "cd /d ""%~dp0frontend-ng"" && npm start"

timeout /t 6 /nobreak >nul
echo.
echo ==========================================================
echo   App is running!
echo   Frontend : http://localhost:4200
echo   API Docs : http://localhost:8000/docs
echo ==========================================================
start "" "http://localhost:4200"
