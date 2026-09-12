#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT_DIR="$(dirname -- "$SCRIPT_DIR")"
PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12+ is required"'
if [ ! -x "$ROOT_DIR/backend/.venv/bin/python" ]; then
  "$PYTHON_BIN" -m venv "$ROOT_DIR/backend/.venv"
fi
"$ROOT_DIR/backend/.venv/bin/python" -m pip install -r "$ROOT_DIR/backend/requirements-dev.lock"
"$ROOT_DIR/backend/.venv/bin/python" -m pip install --no-deps --no-build-isolation -e "$ROOT_DIR/backend"
npm --prefix "$ROOT_DIR/frontend" ci --no-fund
echo "Setup complete. Run scripts/seed.sh, then scripts/dev-backend.sh."
