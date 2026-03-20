#!/usr/bin/env bash

set -e

echo "=========================================="
echo "  FastAPI Backend Setup Script"
echo "=========================================="
echo

echo "[INFO] 当前目录: $(pwd)"
echo

VENV_DIR="./venv"
VENV_PYTHON="$VENV_DIR/bin/python"

# -------------------------------------------------
# 1️⃣ 检查 Python 是否安装
# -------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "[ERROR] 未检测到 Python 环境。"
  echo
  echo "请安装 Python（建议 3.12）"
  exit 1
fi

echo "[INFO] Python 已安装"
"$PYTHON_CMD" --version
echo

# -------------------------------------------------
# 2️⃣ 检查 requirements.txt
# -------------------------------------------------
if [ ! -f requirements.txt ]; then
  echo "[ERROR] 未找到 requirements.txt"
  exit 1
fi

# -------------------------------------------------
# 3️⃣ 初始化 .env
# -------------------------------------------------
if [ ! -f .env ]; then
  if [ -f .env.development ]; then
    echo "[INFO] 未检测到 .env，正在从 .env.development 复制..."
    cp .env.development .env
    echo "[INFO] 已生成 .env"
  else
    echo "[WARN] 未找到 .env，也未找到 .env.development"
  fi
else
  echo "[INFO] .env 已存在，跳过初始化"
fi

echo

# -------------------------------------------------
# 4️⃣ 检查 sqlite3（仅提示，不强制安装）
# -------------------------------------------------
if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "[WARN] 未检测到 sqlite3 命令行工具。"
  echo "[WARN] 如果你需要手动查看 SQLite 数据库，请自行安装 sqlite3。"
else
  echo "[INFO] 已检测到 sqlite3，跳过安装。"
fi

echo

# -------------------------------------------------
# 5️⃣ 创建虚拟环境
# -------------------------------------------------
if [ ! -x "$VENV_PYTHON" ]; then
  echo "[INFO] 创建 Python 虚拟环境..."
  "$PYTHON_CMD" -m venv "$VENV_DIR"
  echo "[INFO] 虚拟环境已创建"
else
  echo "[INFO] 虚拟环境已存在，跳过创建。"
fi

echo

# -------------------------------------------------
# 6️⃣ 使用 venv 中的 Python
# -------------------------------------------------
if [ ! -x "$VENV_PYTHON" ]; then
  echo "[ERROR] 未找到虚拟环境中的 python: $VENV_PYTHON"
  exit 1
fi

echo "[INFO] 当前使用虚拟环境 Python:"
"$VENV_PYTHON" --version
echo

# -------------------------------------------------
# 7️⃣ 安装依赖
# -------------------------------------------------
echo "[INFO] 升级 pip..."
"$VENV_PYTHON" -m pip install --upgrade pip

echo
echo "[INFO] 安装后端依赖（requirements.txt）..."
"$VENV_PYTHON" -m pip install -r requirements.txt

echo
echo "=========================================="
echo "  Setup 完成"
echo "=========================================="
echo

# -------------------------------------------------
# 8️⃣ 启动后端服务
# -------------------------------------------------
echo "[INFO] 启动 uvicorn 开发服务器..."
exec "$VENV_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload