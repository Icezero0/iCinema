#!/usr/bin/env bash
set -euo pipefail

# iCinema frontend dev bootstrap (Linux/macOS)
# - Check Node.js exists + version >= 18
# - Install deps if node_modules or package-lock.json missing
# - Run: npm run dev -- --host

info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
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

# deps check
if [ ! -d "node_modules" ]; then
  info "node_modules not found, installing dependencies..."
  npm install
elif [ ! -f "package-lock.json" ]; then
  warn "package-lock.json not found, reinstalling dependencies..."
  npm install
else
  info "Dependencies already installed."
fi

info "Starting Vite dev server..."
# --host allows access from LAN / mobile devices
npm run dev -- --host
