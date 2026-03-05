#!/bin/bash
set +e
cd "$(dirname "$0")"

echo "Stopping frontend..."
if [ -f .frontend.pid ]; then
  kill "$(cat .frontend.pid)" 2>/dev/null
  rm -f .frontend.pid
fi

echo "Stopping backend..."
if [ -f .backend.pid ]; then
  kill "$(cat .backend.pid)" 2>/dev/null
  rm -f .backend.pid
fi

# Fallback kill (if PID files missing)
pkill -f "uvicorn backend.app.main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null

echo "Stopping MongoDB service..."
brew services stop mongodb-community || true

echo "Stopped."