#!/bin/bash
set +e
cd "$(dirname "$0")"

[ -f .frontend.pid ] && kill "$(cat .frontend.pid)" 2>/dev/null && rm -f .frontend.pid
[ -f .backend.pid ] && kill "$(cat .backend.pid)" 2>/dev/null && rm -f .backend.pid

pkill -f "uvicorn backend.app.main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null