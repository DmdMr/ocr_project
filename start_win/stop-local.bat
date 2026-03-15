@echo off
REM Stop uvicorn/python and vite/node windows (simple approach)
taskkill /FI "WINDOWTITLE eq OCR Backend*" /T /F
taskkill /FI "WINDOWTITLE eq OCR Frontend*" /T /F

REM Optional: stop MongoDB service
net stop MongoDB >nul 2>&1