#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BACKEND_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
VENV_PYTHON="$BACKEND_ROOT/venv/bin/python"

if [ -x "$VENV_PYTHON" ]; then
    PYTHON="$VENV_PYTHON"
else
    PYTHON="${PYTHON:-python3}"
fi

cd "$BACKEND_ROOT"
"$PYTHON" "scripts/migrates/migrate.py"

printf '\n=== Stamping Alembic baseline ===\n'
DEBUG=false "$PYTHON" -m alembic -c "$BACKEND_ROOT/alembic.ini" stamp head

printf '\nMigration completed successfully.\n'
