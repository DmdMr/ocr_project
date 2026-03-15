#!/bin/bash
set +e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
if [ ! -f "$PROJECT_ROOT/backend/requirements.txt" ] && [ -f "$SCRIPT_DIR/../backend/requirements.txt" ]; then
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

cd "$PROJECT_ROOT"
[ -f .frontend.pid ] && kill "$(cat .frontend.pid)" 2>/dev/null && rm -f .frontend.pid
[ -f .backend.pid ] && kill "$(cat .backend.pid)" 2>/dev/null && rm -f .backend.pid

pkill -f "uvicorn backend.app.main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null