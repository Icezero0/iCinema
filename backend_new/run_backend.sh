#!/usr/bin/env bash

set -e

VENV_PYTHON="./venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "[ERROR] Virtual environment was not found. Run ./setup_backend.sh first."
  exit 1
fi

echo "[INFO] Starting uvicorn..."
exec "$VENV_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
