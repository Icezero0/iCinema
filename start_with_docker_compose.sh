#!/bin/bash
# 用于在 Linux/Mac 下一键启动 docker-compose 项目
set -e

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "[iCinema] 正在启动 docker-compose 服务..."
docker-compose up --build
