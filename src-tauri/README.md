# Tauri shell integration

This folder contains the desktop shell for the existing Svelte + FastAPI application.

## Current setup
- On app startup, Tauri checks `127.0.0.1:8000`.
- If backend is not running, Tauri launches it automatically.
- If backend is already running, Tauri reuses it and does not spawn a duplicate process.
- The app waits briefly for backend readiness, then shows the main window.

## Backend command configuration
Default command:
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Override command via environment variable:
```bash
OCR_BACKEND_CMD="<your command here>"
```

This keeps startup modular so we can later switch from Python/Uvicorn to a packaged backend executable without rewriting frontend logic.
