#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT_DIR="$(dirname -- "$SCRIPT_DIR")"
exec "$ROOT_DIR/backend/.venv/bin/python" -m pytest -c "$ROOT_DIR/backend/pyproject.toml" \
  "$ROOT_DIR/backend/tests" "$@"
