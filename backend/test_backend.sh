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

if [ "${1:-}" = "--help-tests" ]; then
  echo "Usage:"
  echo "  ./test_backend.sh"
  echo "  ./test_backend.sh tests/api/test_media_api.py"
  echo "  ./test_backend.sh tests/api/test_media_api.py::test_upload_image_returns_public_url"
  echo "  ./test_backend.sh tests/unit/modules/media -k sticker"
  echo
  echo "Notes:"
  echo "  - No arguments runs the full test suite"
  echo "  - Any other arguments are passed directly to pytest"
  exit 0
fi

echo "[INFO] Installing test dependencies..."
"$VENV_PYTHON" -m pip install -r requirements-dev.txt

echo
if [ "$#" -eq 0 ]; then
  echo "[INFO] Running full pytest suite..."
else
  echo "[INFO] Running pytest with selectors: $*"
fi
exec "$VENV_PYTHON" -m pytest "$@"
