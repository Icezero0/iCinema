#!/usr/bin/env bash

set -e

echo "=========================================="
echo "  FastAPI Backend Setup Script"
echo "=========================================="
echo

echo "[INFO] Current directory: $(pwd)"
echo

VENV_DIR="./venv"
VENV_PYTHON="$VENV_DIR/bin/python"

# -------------------------------------------------
# 1. Check Python
# -------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "[ERROR] Python was not found."
  echo
  echo "Please install Python 3.12 or newer."
  exit 1
fi

echo "[INFO] Python detected"
"$PYTHON_CMD" --version
echo

# -------------------------------------------------
# 2. Check requirements.txt
# -------------------------------------------------
if [ ! -f requirements.txt ]; then
  echo "[ERROR] requirements.txt was not found"
  exit 1
fi

# -------------------------------------------------
# 3. Initialize .env
# -------------------------------------------------
if [ ! -f .env ]; then
  if [ -f .env.development ]; then
    echo "[INFO] .env not found, copying from .env.development..."
    cp .env.development .env
    echo "[INFO] .env created"
  else
    echo "[WARN] Neither .env nor .env.development was found"
  fi
else
  echo "[INFO] .env already exists, skip initialization"
fi

echo

# -------------------------------------------------
# 4. Check sqlite3 (warning only)
# -------------------------------------------------
if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "[WARN] sqlite3 command line tool was not found."
  echo "[WARN] Install sqlite3 manually if you need to inspect the database."
else
  echo "[INFO] sqlite3 detected, skip installation."
fi

echo

# -------------------------------------------------
# 5. Create virtual environment
# -------------------------------------------------
if [ ! -x "$VENV_PYTHON" ]; then
  echo "[INFO] Creating Python virtual environment..."
  "$PYTHON_CMD" -m venv "$VENV_DIR"
  echo "[INFO] Virtual environment created"
else
  echo "[INFO] Virtual environment already exists"
fi

echo

# -------------------------------------------------
# 6. Use Python from venv
# -------------------------------------------------
if [ ! -x "$VENV_PYTHON" ]; then
  echo "[ERROR] Python in virtual environment was not found: $VENV_PYTHON"
  exit 1
fi

echo "[INFO] Using Python from virtual environment:"
"$VENV_PYTHON" --version
echo

# -------------------------------------------------
# 7. Install base dependencies
# -------------------------------------------------
echo "[INFO] Upgrading pip..."
"$VENV_PYTHON" -m pip install --upgrade pip

echo
echo "[INFO] Installing base backend dependencies..."
"$VENV_PYTHON" -m pip install -r requirements.txt

echo
echo "[INFO] Running Alembic upgrade head..."
"$VENV_PYTHON" -m alembic upgrade head

echo
echo "=========================================="
echo "  Setup Complete"
echo "=========================================="
echo
echo "[INFO] Database schema has been upgraded to the latest Alembic revision."
echo "[INFO] Startup will run Alembic again as a safe fallback."
echo
echo "[INFO] Start backend: ./run_backend.sh"
echo "[INFO] Run tests: ./test_backend.sh"
