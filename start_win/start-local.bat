@echo off
setlocal EnableExtensions

REM One-click entrypoint for Windows users.
REM - First run: installs dependencies.
REM - Next runs: starts services quickly.

set "PROJECT_ROOT=%~dp0"
pushd "%PROJECT_ROOT%" >nul 2>&1 || (
  echo [ERROR] Cannot access project folder: %PROJECT_ROOT%
  pause
  exit /b 1
)
set "PROJECT_ROOT=%CD%"

if not exist "backend\requirements.txt" (
  echo [ERROR] Invalid project path: backend\requirements.txt not found.
  echo Make sure this script stays in the project root.
  pause
  popd
  exit /b 1
)

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