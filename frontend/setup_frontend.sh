#!/bin/bash
set -e

echo "[INFO] 正在检查 Node.js 是否已安装..."
if ! command -v node &> /dev/null; then
  echo "[ERROR] Node.js 未安装。请先手动安装：https://nodejs.org"
  exit 1
fi

echo "[INFO] 安装前端依赖..."
npm install

echo "[INFO] 启动 Vite 开发服务器（npm run dev）..."
npm run dev
