#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -z "${DEMO_PASSWORD:-}" ]]; then
  password_file=$(mktemp /tmp/renal-demo-password.XXXXXX)
  chmod 600 "$password_file"
  .venv/bin/python -c 'import secrets,sys; open(sys.argv[1],"w").write(secrets.token_urlsafe(24))' "$password_file"
  DEMO_PASSWORD=$(cat "$password_file")
  export DEMO_PASSWORD
  echo "Local demo password file (do not share in chat/logs): $password_file"
fi
(cd backend && exec ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000) &
backend_pid=$!
(cd frontend && exec npm start) &
frontend_pid=$!
cleanup() { kill "$backend_pid" "$frontend_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
wait -n "$backend_pid" "$frontend_pid"
