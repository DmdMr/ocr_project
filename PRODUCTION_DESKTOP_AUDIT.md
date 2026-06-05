# Production Desktop Deployment Audit

This project is now configured for a portable Electron desktop application that can run on end-user machines without Python, Node.js, npm, or developer tools.

## Recommended backend strategy

Use **PyInstaller backend executable**.

| Strategy | Verdict | Reason |
| --- | --- | --- |
| Bundled Python | Not recommended | Large, fragile, exposes Python environment and dependency resolution problems. |
| PyInstaller backend executable | Recommended | One backend binary per OS/architecture, easiest for Electron to spawn and distribute. |
| Standalone backend service | Not recommended for this app | Adds installer/service permissions, firewall/service lifecycle complexity. |

## Runtime layout

### Packaged resources

```text
OCR Project.app / OCR Project.exe
resources/
  app.asar
  backend-dist/
    ocr-backend(.exe)
  frontend/dist/
    index.html
    assets/...
```

### Writable user data

Electron passes these paths to FastAPI through environment variables:

```text
app.getPath("userData")/
  data/
    ocr_app.db
    ai_ocr_config.json
    ocr_history.jsonl
    training.jsonl
  uploads/
  logs/
    audit.log
    backend-process.log
  dataset/
  model-cache/
```

SQLite, uploads, logs, OCR history, config, and datasets must never be written inside `resources` or `app.asar`.

## Startup sequence

1. Electron resolves `process.resourcesPath` in production.
2. Electron creates writable user-data directories.
3. Electron starts `resources/backend-dist/ocr-backend(.exe)`.
4. Electron polls `http://127.0.0.1:8000/health` until it returns 2xx.
5. Only after health succeeds, Electron loads `http://127.0.0.1:8000`.
6. FastAPI serves `/api`, `/uploads`, and the built Svelte frontend.

## macOS notes

- Build on macOS for macOS artifacts.
- Build both `x64` and `arm64`; do not rely on Rosetta for Apple Silicon.
- Sign and notarize for real distribution outside developer machines.
- If the PyInstaller binary is copied manually, preserve executable permissions with `chmod +x dist/ocr-backend`.
- Unsigned apps downloaded from the internet can be blocked by Gatekeeper/quarantine.

## Windows notes

- Build Windows artifacts on Windows for the cleanest PyInstaller result.
- Use NSIS per-user install to avoid admin rights.
- Code-sign the installer and backend executable to reduce Defender/SmartScreen warnings.
- Binding to `127.0.0.1` avoids most firewall prompts; avoid `0.0.0.0` unless LAN sharing is required.

## Build commands

### Prepare dependencies

```bash
npm install
cd frontend && npm install && cd ..
python -m venv venv
# Windows:
venv\\Scripts\\python -m pip install -r backend/requirements.txt pyinstaller
# macOS:
./venv/bin/python -m pip install -r backend/requirements.txt pyinstaller
```

### macOS Intel + Apple Silicon

Build each architecture with a matching Python/PyInstaller runtime. On Intel macOS, build x64. On Apple Silicon, build arm64. To build x64 on Apple Silicon, run the command under Rosetta with an x64 Python environment.

```bash
# Current machine architecture
npm run dist:mac

# Explicit architecture
npm run dist:mac:x64
npm run dist:mac:arm64
```

Do not package an x64 PyInstaller backend into an arm64 Electron app or the backend will fail to spawn. For a single universal app, build or provide a universal2 backend binary first.

For a signed/notarized distribution, configure these before running electron-builder:

```bash
export CSC_LINK=/path/to/developer-id-app.p12
export CSC_KEY_PASSWORD=...
export APPLE_ID=...
export APPLE_APP_SPECIFIC_PASSWORD=...
export APPLE_TEAM_ID=...
```

### Windows 10/11

Run on Windows:

```powershell
npm run dist:win
```

For signed Windows installers, configure a code-signing certificate for electron-builder.

## OCR assets strategy

The production-safe default is remote Qwen OCR, because it avoids bundling large local models. If offline OCR is required:

1. Keep model files outside `app.asar`.
2. Store bundled model assets under `resources/backend/models` or download them on first run into `app.getPath("userData")/model-cache`.
3. Pass `OCR_MODEL_DIR`, `HF_HOME`, `TRANSFORMERS_CACHE`, and `PADDLE_HOME` from Electron.
4. Provide a UI status screen that shows whether model files are present.

## Files changed

- `electron/main.js` — production backend spawning and health polling.
- `backend/app/main.py` — `/health`, runtime upload/static paths.
- `backend/app/paths.py` — cross-platform runtime/resource path resolution.
- `backend/app/db/database.py` — writable SQLite path.
- `backend/app/api/routes.py` — writable uploads/logs/training paths.
- `backend/app/api/vision_ocr.py` — writable dataset paths.
- `backend/app/services/ocr_service.py` — writable OCR history path.
- `backend/app/services/provider_manager.py` — writable OCR config path and provider helper methods.
- `backend/app/services/trocr_service.py` — model path through `OCR_MODEL_DIR`.
- `backend/desktop_server.py` — PyInstaller entry point.
- `backend/ocr_backend.spec` — PyInstaller spec.
- `package.json` — electron-builder production configuration and build scripts.
- `build/entitlements.mac.plist` — hardened-runtime entitlements template.
