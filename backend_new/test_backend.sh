#!/usr/bin/env bash

set -e

VENV_PYTHON="./venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "[ERROR] Virtual environment was not found. Run ./setup_backend.sh first."
  exit 1
fi

if [ ! -f requirements-dev.txt ]; then
  echo "[ERROR] requirements-dev.txt was not found"
  exit 1
fi

echo "[INFO] Installing test dependencies..."
"$VENV_PYTHON" -m pip install -r requirements-dev.txt

echo
echo "[INFO] Running pytest..."
exec "$VENV_PYTHON" -m pytest "$@"
