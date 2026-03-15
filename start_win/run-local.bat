@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul 2>&1 || (
  echo [ERROR] Cannot access script folder: %SCRIPT_DIR%
  pause
  exit /b 1
)

set "SCRIPT_DIR=%CD%"

set "PROJECT_ROOT=%SCRIPT_DIR%"
if not exist "%PROJECT_ROOT%\backend\requirements.txt" (
  if exist "%SCRIPT_DIR%\..\backend\requirements.txt" (
    set "PROJECT_ROOT=%SCRIPT_DIR%\.."
  )
)
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

if not exist "backend\requirements.txt" (
  echo [ERROR] Invalid project root. Missing backend\requirements.txt
  pause
  popd
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Run install-local.bat first.
  pause
  popd
  exit /b 1
)

set "NPM_CMD="
for /f "delims=" %%I in ('where npm.cmd 2^>nul') do (
  set "NPM_CMD=%%I"
  goto :npm_found
)
if exist "C:\Program Files\nodejs\npm.cmd" set "NPM_CMD=C:\Program Files\nodejs\npm.cmd"
if exist "%LOCALAPPDATA%\Programs\nodejs\npm.cmd" set "NPM_CMD=%LOCALAPPDATA%\Programs\nodejs\npm.cmd"

:npm_found
if "%NPM_CMD%"=="" (
  echo [ERROR] npm is not available in PATH.
  pause
  popd
  exit /b 1
)

net start MongoDB >nul 2>&1

start "OCR Backend" cmd /k "cd /d \"%PROJECT_ROOT%\" && call \".venv\Scripts\activate.bat\" && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
start "OCR Frontend" cmd /k "cd /d \"%PROJECT_ROOT%\frontend\" && \"%NPM_CMD%\" run dev -- --host"

timeout /t 4 >nul
start http://localhost:5173

popd
exit /b 0
