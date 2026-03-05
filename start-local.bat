@echo off
setlocal

cd /d "%~dp0"

REM ---- 1) Start MongoDB service (if installed as Windows service) ----
net start MongoDB >nul 2>&1

REM ---- 2) Backend ----
if not exist ".venv" (
  py -3 -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

start "OCR Backend" cmd /k "cd /d %cd% && call .venv\Scripts\activate.bat && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"

REM ---- 3) Frontend ----
start "OCR Frontend" cmd /k "cd /d %cd%\frontend && npm install && npm run dev -- --host"

REM ---- 4) Open browser ----
timeout /t 4 >nul
start http://localhost:5173

endlocal