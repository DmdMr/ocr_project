@echo off
setlocal EnableExtensions

REM One-click entrypoint for Windows users.
REM - First run: installs dependencies.
REM - Next runs: starts services quickly.

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

if not exist "%PROJECT_ROOT%\backend\requirements.txt" (
  echo [ERROR] Could not find project root from script path.
  echo Expected: backend\requirements.txt
  echo Script dir: %SCRIPT_DIR%
  pause
  popd
  exit /b 1
)

cd /d "%PROJECT_ROOT%"

if not exist ".setup.done" (
  echo [INFO] First run detected. Running installer...
  call "%PROJECT_ROOT%\install-local.bat"
  if errorlevel 1 (
    echo [ERROR] Installation step failed.
    pause
    popd
    exit /b 1
  )
)

call "%PROJECT_ROOT%\run-local.bat"
set "EXIT_CODE=%ERRORLEVEL%"

popd
exit /b %EXIT_CODE%