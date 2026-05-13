const { app, BrowserWindow, dialog } = require("electron")
const { spawn } = require("child_process")
const fs = require("fs")
const http = require("http")
const path = require("path")

const BACKEND_HOST = "127.0.0.1"
const BACKEND_PORT = "8000"
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`

let backendProcess = null

function resolveProjectRoot() {
  // In development Electron runs from the repository root.
  // In packaged builds electron-builder exposes copied backend/frontend files under process.resourcesPath.
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, "..")
}

function resolvePythonExecutable(projectRoot) {
  const configuredPython = process.env.PYTHON_EXECUTABLE
  if (configuredPython) {
    return configuredPython
  }

  const venvPython = process.platform === "win32"
    ? path.join(projectRoot, "venv", "Scripts", "python.exe")
    : path.join(projectRoot, "venv", "bin", "python")

  if (fs.existsSync(venvPython)) {
    return venvPython
  }

  return process.platform === "win32" ? "python" : "python3"
}

function resolvePackagedBackendExecutable(projectRoot) {
  // Future production path: place a PyInstaller executable in release resources and set
  // BACKEND_EXECUTABLE_PATH, or use one of these default locations per platform.
  if (process.env.BACKEND_EXECUTABLE_PATH) {
    return process.env.BACKEND_EXECUTABLE_PATH
  }

  const executableName = process.platform === "win32" ? "ocr-backend.exe" : "ocr-backend"
  const candidates = [
    path.join(projectRoot, "backend-dist", executableName),
    path.join(projectRoot, "backend", "dist", executableName),
  ]

  return candidates.find((candidate) => fs.existsSync(candidate))
}

function startBackend() {
  if (backendProcess) {
    return
  }

  const projectRoot = resolveProjectRoot()
  const packagedBackendExecutable = resolvePackagedBackendExecutable(projectRoot)

  if (packagedBackendExecutable) {
    // Packaged/offline preparation: when a PyInstaller backend executable exists,
    // Electron can run it directly instead of requiring Python on the user's machine.
    backendProcess = spawn(packagedBackendExecutable, [], {
      cwd: projectRoot,
      env: {
        ...process.env,
        HOST: BACKEND_HOST,
        PORT: BACKEND_PORT,
      },
      stdio: "inherit",
      windowsHide: true,
    })
  } else {
    const pythonExecutable = resolvePythonExecutable(projectRoot)

    // Development/default backend start: this launches FastAPI exactly as the web app does,
    // using uvicorn to serve backend.app.main:app on http://127.0.0.1:8000.
    backendProcess = spawn(pythonExecutable, [
      "-m",
      "uvicorn",
      "backend.app.main:app",
      "--host",
      BACKEND_HOST,
      "--port",
      BACKEND_PORT,
    ], {
      cwd: projectRoot,
      env: {
        ...process.env,
        ELECTRON_RUN_AS_DESKTOP: "true",
        FRONTEND_DIST_DIR: path.join(projectRoot, "frontend", "dist"),
      },
      stdio: "inherit",
      windowsHide: true,
    })
  }

  backendProcess.on("exit", (code, signal) => {
    backendProcess = null
    if (!app.isQuitting) {
      console.log(`FastAPI backend exited with code ${code} and signal ${signal}`)
    }
  })
}

function waitForBackend(timeoutMs = 60000) {
  const startedAt = Date.now()

  return new Promise((resolve, reject) => {
    const attempt = () => {
      const request = http.get(BACKEND_URL, (response) => {
        response.resume()
        resolve()
      })

      request.on("error", () => {
        if (Date.now() - startedAt > timeoutMs) {
          reject(new Error(`FastAPI backend did not become ready at ${BACKEND_URL}`))
          return
        }

        setTimeout(attempt, 500)
      })

      request.setTimeout(2000, () => {
        request.destroy()
      })
    }

    attempt()
  })
}

function createWindow() {
  // Electron owns the desktop shell: it creates the application window and points it
  // at the FastAPI server, which can serve API routes, uploads, and the built Svelte UI.
  const mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  mainWindow.loadURL(BACKEND_URL)
}

function stopBackend() {
  if (!backendProcess) {
    return
  }

  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", backendProcess.pid, "/f", "/t"])
  } else {
    backendProcess.kill("SIGTERM")
  }

  backendProcess = null
}

app.whenReady().then(async () => {
  startBackend()

  try {
    await waitForBackend()
    createWindow()
  } catch (error) {
    dialog.showErrorBox("OCR backend failed to start", error.message)
    app.quit()
  }

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on("before-quit", () => {
  app.isQuitting = true
  stopBackend()
})

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit()
  }
})
