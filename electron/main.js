const { app, BrowserWindow, dialog } = require("electron")
const { spawn } = require("child_process")
const fs = require("fs")
const http = require("http")
const os = require("os")
const path = require("path")

const APP_NAME = "OCR Project"
const BACKEND_BIND_HOST = process.env.OCR_BACKEND_BIND_HOST || "127.0.0.1"
const BACKEND_WINDOW_HOST = "127.0.0.1"
const BACKEND_PORT = process.env.OCR_BACKEND_PORT || "8000"
const BACKEND_URL = `http://${BACKEND_WINDOW_HOST}:${BACKEND_PORT}`
const BACKEND_HEALTH_URL = `${BACKEND_URL}/health`
const BACKEND_START_TIMEOUT_MS = Number(process.env.OCR_BACKEND_START_TIMEOUT_MS || 120000)

let backendProcess = null
let backendOwnedByElectron = false
let mainWindow = null

function resolveResourceRoot() {
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, "..")
}

function resolveFrontendDistDir(resourceRoot) {
  return path.join(resourceRoot, "frontend", "dist")
}

function resolveBackendExecutable(resourceRoot) {
  if (process.env.BACKEND_EXECUTABLE_PATH) {
    return process.env.BACKEND_EXECUTABLE_PATH
  }

  const executableName = process.platform === "win32" ? "ocr-backend.exe" : "ocr-backend"
  const candidates = [
    path.join(resourceRoot, "backend-dist", executableName),
    path.join(resourceRoot, "backend", "dist", executableName),
  ]

  return candidates.find((candidate) => fs.existsSync(candidate))
}

function resolvePythonExecutable(resourceRoot) {
  if (process.env.PYTHON_EXECUTABLE) {
    return process.env.PYTHON_EXECUTABLE
  }

  const venvPython = process.platform === "win32"
    ? path.join(resourceRoot, "venv", "Scripts", "python.exe")
    : path.join(resourceRoot, "venv", "bin", "python")

  if (fs.existsSync(venvPython)) {
    return venvPython
  }

  return process.platform === "win32" ? "python" : "python3"
}

function detectLocalIPv4() {
  for (const entries of Object.values(os.networkInterfaces())) {
    for (const entry of entries || []) {
      if (entry.family === "IPv4" && !entry.internal) {
        return entry.address
      }
    }
  }
  return BACKEND_WINDOW_HOST
}

function buildBackendEnvironment(resourceRoot) {
  const userDataDir = app.getPath("userData")
  const uploadDir = path.join(userDataDir, "uploads")
  const dataDir = path.join(userDataDir, "data")
  const logsDir = path.join(userDataDir, "logs")
  const datasetDir = path.join(userDataDir, "dataset")
  const modelDir = path.join(resourceRoot, "backend", "models")

  for (const dir of [uploadDir, dataDir, logsDir, datasetDir]) {
    fs.mkdirSync(dir, { recursive: true })
  }

  return {
    ...process.env,
    ELECTRON_RUN_AS_DESKTOP: "true",
    HOST: BACKEND_BIND_HOST,
    PORT: BACKEND_PORT,
    LOCAL_NETWORK_URL: `http://${detectLocalIPv4()}:${BACKEND_PORT}`,
    OCR_APP_RESOURCES_DIR: resourceRoot,
    OCR_APP_DATA_DIR: userDataDir,
    FRONTEND_DIST_DIR: resolveFrontendDistDir(resourceRoot),
    UPLOAD_DIR: uploadDir,
    OCR_DATA_DIR: dataDir,
    AUDIT_LOG_DIR: logsDir,
    OCR_DATASET_DIR: datasetDir,
    OCR_MODEL_DIR: modelDir,
    SQLITE_DB_PATH: path.join(dataDir, "ocr_app.db"),
    AI_OCR_CONFIG_PATH: path.join(dataDir, "ai_ocr_config.json"),
    OCR_HISTORY_PATH: path.join(dataDir, "ocr_history.jsonl"),
    OCR_TRAINING_DATA_PATH: path.join(dataDir, "training.jsonl"),
    TRANSFORMERS_CACHE: path.join(userDataDir, "model-cache", "transformers"),
    HF_HOME: path.join(userDataDir, "model-cache", "huggingface"),
    PADDLE_HOME: path.join(userDataDir, "model-cache", "paddle"),
    PYTHONUNBUFFERED: "1",
  }
}

function requestUrl(url, timeoutMs = 2000) {
  return new Promise((resolve) => {
    const request = http.get(url, (response) => {
      response.resume()
      resolve({ ok: response.statusCode >= 200 && response.statusCode < 300, statusCode: response.statusCode })
    })

    request.on("error", (error) => resolve({ ok: false, error }))
    request.setTimeout(timeoutMs, () => {
      request.destroy()
      resolve({ ok: false, error: new Error(`Timed out while requesting ${url}`) })
    })
  })
}

async function isBackendHealthy() {
  const result = await requestUrl(BACKEND_HEALTH_URL, 1500)
  return result.ok
}

function attachBackendLogging(child) {
  if (!app.isPackaged) {
    return
  }

  const logFile = path.join(app.getPath("userData"), "backend-process.log")
  const appendLog = (prefix, chunk) => {
    fs.appendFile(logFile, `[${new Date().toISOString()}] ${prefix}: ${chunk}`, () => {})
  }

  child.stdout?.on("data", (chunk) => appendLog("stdout", chunk))
  child.stderr?.on("data", (chunk) => appendLog("stderr", chunk))
}

async function startBackend() {
  if (backendProcess || await isBackendHealthy()) {
    backendOwnedByElectron = false
    return
  }

  const resourceRoot = resolveResourceRoot()
  const env = buildBackendEnvironment(resourceRoot)
  const packagedBackendExecutable = resolveBackendExecutable(resourceRoot)

  if (packagedBackendExecutable) {
    backendProcess = spawn(packagedBackendExecutable, [], {
      cwd: resourceRoot,
      env,
      stdio: app.isPackaged ? ["ignore", "pipe", "pipe"] : "inherit",
      windowsHide: true,
    })
  } else {
    if (app.isPackaged) {
      throw new Error(
        `Packaged backend executable was not found. Expected ocr-backend in ${path.join(resourceRoot, "backend-dist")}. ` +
        "Build it with PyInstaller before running electron-builder."
      )
    }

    const pythonExecutable = resolvePythonExecutable(resourceRoot)
    backendProcess = spawn(pythonExecutable, ["-m", "backend.desktop_server"], {
      cwd: resourceRoot,
      env,
      stdio: "inherit",
      windowsHide: true,
    })
  }

  backendOwnedByElectron = true
  attachBackendLogging(backendProcess)

  backendProcess.on("exit", (code, signal) => {
    backendProcess = null
    if (!app.isQuitting) {
      console.log(`FastAPI backend exited with code ${code} and signal ${signal}`)
    }
  })
}

async function waitForBackend(timeoutMs = BACKEND_START_TIMEOUT_MS) {
  const startedAt = Date.now()
  let lastError = null

  while (Date.now() - startedAt < timeoutMs) {
    const result = await requestUrl(BACKEND_HEALTH_URL, 2000)
    if (result.ok) {
      return
    }
    lastError = result.error || new Error(`HTTP ${result.statusCode}`)
    await new Promise((resolve) => setTimeout(resolve, 500))
  }

  throw new Error(
    `Backend not ready after ${Math.round(timeoutMs / 1000)} seconds at ${BACKEND_HEALTH_URL}. ` +
    `Last error: ${lastError?.message || "unknown"}. ` +
    `Backend logs: ${path.join(app.getPath("userData"), "backend-process.log")}`
  )
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    autoHideMenuBar: app.isPackaged,
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  mainWindow.once("ready-to-show", () => mainWindow.show())
  mainWindow.on("closed", () => { mainWindow = null })
  mainWindow.loadURL(BACKEND_URL)
}

function stopBackend() {
  if (!backendProcess || !backendOwnedByElectron) {
    return
  }

  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"], { windowsHide: true })
  } else {
    backendProcess.kill("SIGTERM")
  }

  backendProcess = null
}

app.setName(APP_NAME)

app.whenReady().then(async () => {
  try {
    await startBackend()
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
