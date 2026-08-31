@echo off
setlocal

set "ROOT=%~dp0"

echo ==========================================================
echo   Bootstrap Build Runner
echo ==========================================================
echo Preparing machine for execution...

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Get-Item -LiteralPath '%ROOT%build_exe.bat' | Unblock-File -ErrorAction SilentlyContinue; Get-ChildItem -LiteralPath '%ROOT%' -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue; exit 0 } catch { exit 0 }" >nul 2>nul

echo Running build_exe.bat...
call "%ROOT%build_exe.bat"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
  echo.
  echo Build failed with exit code %EXITCODE%.
)

endlocal & exit /b %EXITCODE%
