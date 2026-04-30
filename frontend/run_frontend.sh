#!/usr/bin/env bash
set -euo pipefail

info() { echo "[INFO] $*"; }
error() { echo "[ERROR] $*"; }

info "Checking Node.js..."
if ! command -v node >/dev/null 2>&1; then
  error "Node.js not found. Please install from https://nodejs.org"
  exit 1
fi

NODE_VERSION="$(node -v)"
NODE_MAJOR="${NODE_VERSION#v}"
NODE_MAJOR="${NODE_MAJOR%%.*}"

if [ "${NODE_MAJOR}" -lt 18 ]; then
  error "Node.js >= 18 is required. Current: ${NODE_VERSION}"
  exit 1
fi

if [ ! -d "node_modules" ]; then
  error "Dependencies are not installed. Please run ./setup_frontend.sh first."
  exit 1
fi

info "Starting Vite dev server..."
npm run dev -- --host
