#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="${ROOT}/backend:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
  nvm use 20 >/dev/null 2>&1 || true
fi

mkdir -p "${ROOT}/backend/data/uploads" "${ROOT}/backend/data/samples"

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir "${ROOT}/backend" --workers 1 &
API_PID=$!

cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT

for i in $(seq 1 60); do
  if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

export HOSTNAME="${HOSTNAME:-0.0.0.0}"
export PORT="${PORT:-3000}"
export INTERNAL_API_URL="${INTERNAL_API_URL:-http://127.0.0.1:8000}"
cd "${ROOT}/frontend/.next/standalone"
exec node server.js
