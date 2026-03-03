#!/bin/bash
set -e

echo "[INFO] 当前目录: $(pwd)"
VENV_DIR="./venv"

#------------------------------------------
# [1] 安装 sqlite3（如果未安装）
#------------------------------------------
if ! command -v sqlite3 &>/dev/null; then
  echo "[INFO] 未检测到 sqlite3，正在尝试安装..."
  if command -v apt &>/dev/null; then
    sudo apt update
    sudo apt install -y sqlite3
  elif command -v yum &>/dev/null; then
    sudo yum install -y sqlite
  else
    echo "[ERROR] 不支持的包管理器，请手动安装 sqlite3。"
    exit 1
  fi
else
  echo "[INFO] 已检测到 sqlite3，跳过安装。"
fi

#------------------------------------------
# [2] 创建虚拟环境（如果不存在）
#------------------------------------------
if [ ! -f "$VENV_DIR/bin/activate" ]; then
  echo "[INFO] 创建 Python 虚拟环境..."
  python3 -m venv "$VENV_DIR"
else
  echo "[INFO] 虚拟环境已存在，跳过创建。"
fi

#------------------------------------------
# [3] 激活虚拟环境
#------------------------------------------
source "$VENV_DIR/bin/activate"

#------------------------------------------
# [4] 安装依赖
#------------------------------------------
echo "[INFO] 安装后端依赖（requirements.txt）..."
python -m pip install --upgrade pip
pip install -r requirements.txt

#------------------------------------------
# [5] 启动后端服务
#------------------------------------------
echo "[INFO] 启动 uvicorn 开发服务器..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
