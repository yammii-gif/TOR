#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install --cache-dir /tmp/renal-pip-cache -r backend/requirements.txt
npm --prefix frontend ci --cache /tmp/renal-npm-cache --no-audit --no-fund
npm --prefix frontend run build
