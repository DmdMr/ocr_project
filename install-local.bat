@echo off
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0"
pushd "%PROJECT_ROOT%" >nul 2>&1 || (
  echo [ERROR] Cannot access project folder: %PROJECT_ROOT%
  pause
  exit /b 1
)
set "PROJECT_ROOT=%CD%"

if not exist "backend\requirements.txt" (
  echo [ERROR] Invalid project root. Missing backend\requirements.txt
  pause
  popd
  exit /b 1
)
if not exist "frontend\package.json" (
  echo [ERROR] Invalid project root. Missing frontend\package.json
  pause
  popd
  exit /b 1
)

REM ---- Python detection ----
set "PYTHON_CMD="
where py >nul 2>&1 && set "PYTHON_CMD=py -3"
if "%PYTHON_CMD%"=="" where python >nul 2>&1 && set "PYTHON_CMD=python"

if "%PYTHON_CMD%"=="" (
  echo [ERROR] Python 3.10+ is not available in PATH.
  pause
  popd
  exit /b 1
)

echo Using Python: %PYTHON_CMD%

REM ---- Node / npm detection ----
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

echo Using npm: %NPM_CMD%

REM ---- Backend install ----
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv
    pause
    popd
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] Failed to upgrade pip.
  pause
  popd
  exit /b 1
)

pip install -r backend\requirements.txt
if errorlevel 1 (
  echo [ERROR] Failed to install backend dependencies.
  pause
  popd
  exit /b 1
)

REM ---- Frontend install ----
pushd "frontend"
if exist "package-lock.json" (
  call "%NPM_CMD%" ci
) else (
  call "%NPM_CMD%" install
)
if errorlevel 1 (
  echo [ERROR] Failed to install frontend dependencies.
  pause
  popd
  popd
  exit /b 1
)
popd

echo setup complete > ".setup.done"
echo [OK] Installation complete. You can now run run-local.bat any time.

popd
exit /b 0
