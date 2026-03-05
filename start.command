#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Starting MongoDB..."
brew services start mongodb-community || true

echo "Setting up Python venv..."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

echo "Starting backend (uvicorn on :8000)..."
nohup python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
echo $! > .backend.pid

echo "Starting frontend (vite on :5173)..."
cd frontend
npm install
nohup npm run dev -- --host > ../frontend.log 2>&1 &
echo $! > ../.frontend.pid
cd ..

sleep 3
open http://localhost:5173
echo "App started."