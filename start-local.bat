@echo off
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

REM ---- 1) Start MongoDB service (if installed as Windows service) ----
net start MongoDB >nul 2>&1

REM ---- 2) Resolve Python command ----
set "PYTHON_CMD="
where py >nul 2>&1 && set "PYTHON_CMD=py -3"
if "%PYTHON_CMD%"=="" (
  where python >nul 2>&1 && set "PYTHON_CMD=python"
)

if "%PYTHON_CMD%"=="" (
  echo [ERROR] Python is not available in PATH.
  echo Install Python 3.10+ and restart terminal/VS Code.
  pause
  exit /b 1
)

echo Using Python: %PYTHON_CMD%

REM ---- 3) Backend ----
if not exist ".venv\Scripts\python.exe" (
  %PYTHON_CMD% -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

start "OCR Backend" cmd /k "cd /d \"%PROJECT_ROOT%\" && call \".venv\Scripts\activate.bat\" && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"

REM ---- 4) Frontend ----
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
  echo Install Node.js LTS and then restart terminal/VS Code.
  echo Expected npm at one of:
  echo   - C:\Program Files\nodejs\npm.cmd
  echo   - %%LOCALAPPDATA%%\Programs\nodejs\npm.cmd
  pause
  exit /b 1
)

echo Using npm: %NPM_CMD%
start "OCR Frontend" cmd /k "cd /d \"%PROJECT_ROOT%frontend\" && \"%NPM_CMD%\" install && \"%NPM_CMD%\" run dev -- --host"

REM ---- 5) Open browser ----
timeout /t 4 >nul
start http://localhost:5173

endlocal
