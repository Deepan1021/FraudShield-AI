#!/usr/bin/env bash
# macOS / Linux launcher.  ./run.sh [prod|seed]
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "Python 3.10+ required"; exit 1; }
command -v npm >/dev/null || { echo "Node.js 18+ required"; exit 1; }
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -q -r backend/requirements.txt
[ -f .env ] || cp .env.example .env
[ -d frontend/node_modules ] || (cd frontend && npm install --no-audit --no-fund)
.venv/bin/python scripts/init_db.py
[ "${1:-}" = "seed" ] && .venv/bin/python scripts/seed_demo.py
if [ "${1:-}" = "prod" ]; then
  (cd frontend && npm run build)
  SERVE_FRONTEND=true exec .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
fi
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload --reload-dir backend &
API=$!
trap 'kill $API 2>/dev/null' EXIT
(cd frontend && npm run dev)
