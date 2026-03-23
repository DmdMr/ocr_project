const { spawn } = require("child_process");

const isWin = process.platform === "win32";

const frontend = spawn(
  "npm",
  ["run", "dev", "--", "--host", "0.0.0.0"],
  {
    cwd: "frontend",
    stdio: "inherit",
    shell: true
  }
);

const backendCommand = isWin
  ? 'venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000'
  : './venv/bin/python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000';

const backend = spawn(backendCommand, {
  stdio: "inherit",
  shell: true
});

function shutdown() {
  frontend.kill();
  backend.kill();
  process.exit();
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);