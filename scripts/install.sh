#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m venv .venv
.venv/bin/pip install --cache-dir /tmp/renal-pip-cache -r backend/requirements.txt
(cd backend && ../.venv/bin/alembic upgrade head && ../.venv/bin/python -c 'from app.db import seed; seed()')
(cd frontend && npm ci --cache /tmp/npm-cache --no-audit --no-fund && npm run build)
