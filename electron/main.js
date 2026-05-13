const { app, BrowserWindow, dialog } = require("electron")
const { spawn } = require("child_process")
const fs = require("fs")
const http = require("http")
const os = require("os")
const path = require("path")

const BACKEND_BIND_HOST = "0.0.0.0"
const BACKEND_WINDOW_HOST = "127.0.0.1"
const BACKEND_PORT = "8000"
const BACKEND_URL = `http://${BACKEND_WINDOW_HOST}:${BACKEND_PORT}`

let backendProcess = null
let backendOwnedByElectron = false

function resolveProjectRoot() {
  // In development Electron runs from the repository root.
  // In packaged builds electron-builder exposes copied backend/frontend files under process.resourcesPath.
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, "..")
}

function detectLocalIPv4() {
  const interfaces = os.networkInterfaces()

  for (const entries of Object.values(interfaces)) {
    for (const entry of entries || []) {
      if (entry.family === "IPv4" && !entry.internal) {
        return entry.address
      }
    }
  }

  return BACKEND_WINDOW_HOST
}

function isBackendOnline() {
  return new Promise((resolve) => {
    const request = http.get(BACKEND_URL, (response) => {
      response.resume()
      resolve(true)
    })

    request.on("error", () => resolve(false))
    request.setTimeout(1000, () => {
      request.destroy()
      resolve(false)
    })
  })
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

async function startBackend() {
  if (backendProcess) {
    return
  }

  // Avoid duplicate backend instances: if port 8000 is already serving the app,
  // Electron reuses it for the desktop window and will not kill it on exit.
  if (await isBackendOnline()) {
    backendOwnedByElectron = false
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
        HOST: BACKEND_BIND_HOST,
        PORT: BACKEND_PORT,
        LOCAL_NETWORK_URL: `http://${detectLocalIPv4()}:${BACKEND_PORT}`,
      },
      stdio: app.isPackaged ? "ignore" : "inherit",
      windowsHide: true,
    })
  } else {
    const pythonExecutable = resolvePythonExecutable(projectRoot)

    // Development/default backend start: this launches FastAPI exactly as the web app does,
    // binding uvicorn to 0.0.0.0:8000 so other LAN devices can connect.
    backendProcess = spawn(pythonExecutable, [
      "-m",
      "uvicorn",
      "backend.app.main:app",
      "--host",
      BACKEND_BIND_HOST,
      "--port",
      BACKEND_PORT,
    ], {
      cwd: projectRoot,
      env: {
        ...process.env,
        ELECTRON_RUN_AS_DESKTOP: "true",
        FRONTEND_DIST_DIR: path.join(projectRoot, "frontend", "dist"),
        LOCAL_NETWORK_URL: `http://${detectLocalIPv4()}:${BACKEND_PORT}`,
      },
      stdio: app.isPackaged ? "ignore" : "inherit",
      windowsHide: true,
    })
  }

  backendOwnedByElectron = true

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
  // at the FastAPI server, which serves API routes, uploads, the built Svelte UI,
  // and the LAN-shareable browser URL shown in the sidebar.
  const mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    autoHideMenuBar: app.isPackaged,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  mainWindow.loadURL(BACKEND_URL)
}

function stopBackend() {
  if (!backendProcess || !backendOwnedByElectron) {
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
  await startBackend()

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
