#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT_DIR="$(dirname -- "$SCRIPT_DIR")"
exec "$ROOT_DIR/backend/.venv/bin/python" -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --reload --reload-dir "$ROOT_DIR/backend/app"
