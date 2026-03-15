#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
if [ ! -f "$PROJECT_ROOT/backend/requirements.txt" ] && [ -f "$SCRIPT_DIR/../backend/requirements.txt" ]; then
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

if [ ! -f "$PROJECT_ROOT/backend/requirements.txt" ]; then
  echo "[ERROR] Could not find project root from script path: $SCRIPT_DIR"
  exit 1
fi

cd "$PROJECT_ROOT"

# ---------------------------
# Functions
# ---------------------------
kill_if_running() {
    local pidfile="$1"
    if [ -f "$pidfile" ]; then
        local pid
        pid=$(cat "$pidfile")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "Stopping process $pid..."
            kill -9 "$pid" || true
        fi
        rm -f "$pidfile"
    fi
}

clean_logs() {
    local logfile="$1"
    if [ -f "$logfile" ]; then
        rm -f "$logfile"
    fi
}

# ---------------------------
# Stop previous processes
# ---------------------------
kill_if_running ".backend.pid"
kill_if_running ".frontend.pid"

# ---------------------------
# Clean old logs
# ---------------------------
clean_logs "backend.log"
clean_logs "frontend.log"

# ---------------------------
# Start MongoDB
# ---------------------------
echo "==> Starting MongoDB..."
brew services start mongodb-community >/dev/null 2>&1 || true

# ---------------------------
# Setup Python virtual environment
# ---------------------------
if [ -d "venv" ]; then
  ENV_DIR="venv"
elif [ -d ".venv" ]; then
  ENV_DIR=".venv"
else
  ENV_DIR="venv"
  echo "Creating virtual environment..."
  python3 -m venv "$ENV_DIR"
fi

echo "==> Using virtualenv: $ENV_DIR"
source "$ENV_DIR/bin/activate"

# ---------------------------
# Install backend dependencies
# ---------------------------
echo "==> Installing backend dependencies..."
python -m pip install --upgrade pip >/dev/null
pip install -r backend/requirements.txt >/dev/null
pip install transformers >/dev/null 2>&1 || true

# ---------------------------
# Start backend
# ---------------------------
echo "==> Starting backend on 0.0.0.0:8000..."
nohup python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
echo $! > .backend.pid

# ---------------------------
# Start frontend
# ---------------------------
echo "==> Starting frontend on 0.0.0.0:5173..."
cd frontend
npm install >/dev/null
nohup npm run dev -- --host 0.0.0.0 --port 5173 > ../frontend.log 2>&1 &
echo $! > ../.frontend.pid
cd ..

# ---------------------------
# Wait a few seconds and open browser
# ---------------------------
sleep 3
echo "==> Opening frontend in browser..."
open http://localhost:5173

echo "✅ Project started successfully!"
echo "Logs: backend.log, frontend.log"
echo "PIDs: .backend.pid, .frontend.pid"
