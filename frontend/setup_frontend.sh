#!/usr/bin/env bash
set -euo pipefail

# iCinema frontend setup (Linux/macOS)
# - Check Node.js exists + version >= 18
# - Install dependencies
# - Leave dev server startup to run_frontend.sh

info() { echo "[INFO] $*"; }
error() { echo "[ERROR] $*"; }

info "Checking Node.js..."
if ! command -v node >/dev/null 2>&1; then
  error "Node.js not found. Please install from https://nodejs.org"
  exit 1
fi

# Node major version (>= 18)
NODE_VERSION="$(node -v)"          # e.g. v20.11.1
NODE_MAJOR="${NODE_VERSION#v}"     # 20.11.1
NODE_MAJOR="${NODE_MAJOR%%.*}"     # 20

if [ "${NODE_MAJOR}" -lt 18 ]; then
  error "Node.js >= 18 is required. Current: ${NODE_VERSION}"
  exit 1
fi

# deps install
info "Installing dependencies..."
if [ -f "package-lock.json" ]; then
  npm ci
else
  npm install
fi

info "Frontend dependencies are ready."
info "Run ./run_frontend.sh to start the Vite dev server."
