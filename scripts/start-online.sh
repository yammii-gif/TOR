#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DEMO_PASSWORD:?Set DEMO_PASSWORD in hosting environment settings}"
backend_port="${BACKEND_PORT:-8000}"
web_port="${PORT:-3000}"
export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:$backend_port}"

(cd backend && python -m alembic upgrade head && python -c 'from app.db import seed; seed()')
(cd backend && exec python -m uvicorn app.main:app --host 127.0.0.1 --port "$backend_port") &
backend_pid=$!
frontend_pid=''
cleanup() {
  kill "$backend_pid" ${frontend_pid:+"$frontend_pid"} 2>/dev/null || true
  wait "$backend_pid" ${frontend_pid:+"$frontend_pid"} 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

python - "$backend_port" <<'PY'
import json, sys, time, urllib.request
url = 'http://127.0.0.1:' + sys.argv[1] + '/health'
for _ in range(50):
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            if json.load(response).get('mode') == 'SYNTHETIC DATA':
                break
    except (OSError, ValueError):
        pass
    time.sleep(0.2)
else:
    raise SystemExit('Synthetic backend did not become ready')
PY

(cd frontend && exec node node_modules/next/dist/bin/next start --hostname 0.0.0.0 --port "$web_port") &
frontend_pid=$!
wait -n "$backend_pid" "$frontend_pid"
