#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="${ROOT}/backend:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1

mkdir -p "${ROOT}/backend/data/uploads" "${ROOT}/backend/data/samples"

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir "${ROOT}/backend" &
API_PID=$!

cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT

for i in $(seq 1 40); do
  if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

cd "${ROOT}/frontend"
if [ ! -d node_modules ]; then
  npm install
fi
npm run dev
