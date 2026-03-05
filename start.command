#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Starting MongoDB..."
brew services start mongodb-community >/dev/null 2>&1 || true

# pick existing env: venv first, then .venv, else create venv
if [ -d "venv" ]; then
  ENV_DIR="venv"
elif [ -d ".venv" ]; then
  ENV_DIR=".venv"
else
  ENV_DIR="venv"
  python3 -m venv "$ENV_DIR"
fi

echo "==> Using virtualenv: $ENV_DIR"
source "$ENV_DIR/bin/activate"

echo "==> Installing backend deps..."
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

# optional safety if your local ocr_service uses transformers
pip install transformers >/dev/null 2>&1 || true

echo "==> Starting backend..."
nohup python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
echo $! > .backend.pid

echo "==> Starting frontend..."
cd frontend
npm install
nohup npm run dev -- --host > ../frontend.log 2>&1 &
echo $! > ../.frontend.pid
cd ..

sleep 3
open http://localhost:5173
echo "✅ Started. Logs: backend.log, frontend.log"