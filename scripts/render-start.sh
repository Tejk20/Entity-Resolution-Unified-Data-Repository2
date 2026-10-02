#!/bin/bash
set -euo pipefail

ROOT="${APP_ROOT:-/app}"
export PYTHONPATH="${ROOT}/backend:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1
export HOSTNAME="${HOSTNAME:-0.0.0.0}"
export PORT="${PORT:-3000}"

mkdir -p "${ROOT}/backend/data/uploads" "${ROOT}/backend/data/samples"

python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir "${ROOT}/backend" --workers 1 &
API_PID=$!

cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT

for i in $(seq 1 60); do
  if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

cd "${ROOT}/frontend"
exec node server.js
