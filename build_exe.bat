@echo off
setlocal EnableDelayedExpansion

echo ==========================================================
echo   Kanini Resume Builder - EXE Build
echo ==========================================================
echo.

set ROOT=%~dp0
set PYTHON=C:/Users/IndiraEswaran/AppData/Local/Python/pythoncore-3.14-64/python.exe
set "AUTO_LAUNCH_AFTER_BUILD=1"

echo [0/8] Preparing machine for script execution...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Get-Item -LiteralPath '%~f0' | Unblock-File -ErrorAction SilentlyContinue; Get-ChildItem -LiteralPath '%ROOT%' -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue; exit 0 } catch { exit 0 }" >nul 2>nul

if not exist "%PYTHON%" (
  echo [ERROR] Python executable not found at:
  echo         %PYTHON%
  exit /b 1
)

echo [1/5] Installing backend dependencies...
%PYTHON% -m pip install -r "%ROOT%backend\requirements.txt"
if errorlevel 1 exit /b 1

echo [2/5] Installing PyInstaller...
%PYTHON% -m pip install --user pyinstaller
if errorlevel 1 exit /b 1

echo [3/5] Building Angular frontend (production)...
cd /d "%ROOT%frontend-ng"
call npm install
if errorlevel 1 exit /b 1
call npm run build
if errorlevel 1 exit /b 1

set FRONTEND_DIST=%ROOT%frontend-ng\dist\frontend-ng\browser
if not exist "%FRONTEND_DIST%\index.html" (
  set FRONTEND_DIST=%ROOT%frontend-ng\dist\frontend-ng
)

if not exist "%FRONTEND_DIST%\index.html" (
  echo [ERROR] Angular build output not found.
  exit /b 1
)

echo [4/5] Creating executable...
cd /d "%ROOT%"
%PYTHON% -m PyInstaller --noconfirm --clean --onedir --name KaniniResumeBuilder ^
  --collect-all chromadb ^
  --add-data "%FRONTEND_DIST%;frontend-dist" ^
  "%ROOT%backend\main.py"
if errorlevel 1 exit /b 1

echo [5/6] Copying frontend assets into packaged folder...
if not exist "%ROOT%dist\KaniniResumeBuilder\_internal\frontend-dist" mkdir "%ROOT%dist\KaniniResumeBuilder\_internal\frontend-dist"
xcopy "%FRONTEND_DIST%\*" "%ROOT%dist\KaniniResumeBuilder\_internal\frontend-dist\" /E /I /Y /Q >nul
if errorlevel 1 exit /b 1

echo [6/7] Creating launcher batch file...
set "LAUNCHER=%ROOT%dist\KaniniResumeBuilder\Launch-KaniniResumeBuilder.bat"
(
  echo @echo off
  echo setlocal EnableDelayedExpansion
  echo.
  echo set "EXE_DIR=%%~dp0"
  echo set "APP_EXE=%%EXE_DIR%%KaniniResumeBuilder.exe"
  echo set "APP_URL=http://localhost:8000"
  echo set "HEALTH_URL=%%APP_URL%%/api/health"
  echo.
  echo rem Set to 0 if you do not want the browser to open automatically.
  echo set "OPEN_BROWSER=1"
  echo set "BROWSER_DELAY_SECONDS=2"
  echo set "STARTUP_TIMEOUT_SECONDS=30"
  echo.
  echo if not exist "%%APP_EXE%%" ^(
  echo     echo [ERROR] Could not find: %%APP_EXE%%
  echo     pause
  echo     exit /b 1
  echo ^)
  echo.
  echo echo Starting Kanini Resume Builder...
  echo start "" "%%APP_EXE%%"
  echo.
  echo if "%%OPEN_BROWSER%%"=="1" ^(
  echo     set /a "_WAITED=0"
  echo     :wait_for_health
  echo     powershell -NoProfile -ExecutionPolicy Bypass -Command "try { (Invoke-WebRequest -UseBasicParsing '%%HEALTH_URL%%' -TimeoutSec 2) ^| Out-Null; exit 0 } catch { exit 1 }"
  echo     if not errorlevel 1 goto open_browser
  echo     if ^!_WAITED^! GEQ ^!STARTUP_TIMEOUT_SECONDS^! goto open_browser
  echo     timeout /t 1 /nobreak ^>nul
  echo     set /a "_WAITED+=1"
  echo     goto wait_for_health
  echo.
  echo     :open_browser
  echo     timeout /t %%BROWSER_DELAY_SECONDS%% /nobreak ^>nul
  echo     start "" "%%APP_URL%%"
  echo ^)
  echo.
  echo echo Launched.
  echo echo URL: %%APP_URL%%
  echo echo Note: open localhost, not 0.0.0.0
  echo exit /b 0
) > "%LAUNCHER%"
if errorlevel 1 exit /b 1

echo [7/7] Build complete.
echo.
echo Executable folder:
echo   %ROOT%dist\KaniniResumeBuilder
echo.
echo Run this file:
echo   %ROOT%dist\KaniniResumeBuilder\KaniniResumeBuilder.exe
echo.
echo API and app URL:
echo   http://localhost:8000
echo   (Use localhost in browser; 0.0.0.0 is server bind address only)
echo.

if "%AUTO_LAUNCH_AFTER_BUILD%"=="1" (
  echo [8/8] Launching app and opening browser...
  start "" "%ROOT%dist\KaniniResumeBuilder\Launch-KaniniResumeBuilder.bat"
)

endlocal
