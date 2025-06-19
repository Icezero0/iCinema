@echo off
chcp 65001 >nul
setlocal

echo [INFO] 当前目录为 %cd%
set VENV_DIR=venv

::------------------------------------------
:: [1] 安装 SQLite3（如果未安装）
::------------------------------------------
where sqlite3 >nul 2>nul
if errorlevel 1 (
    echo [INFO] 未检测到 sqlite3，正在下载并安装...

    set SQLITE_URL=https://www.sqlite.org/2024/sqlite-tools-win-x64-3440200.zip
    set SQLITE_ZIP=sqlite.zip
    set SQLITE_DIR=sqlite-tools

    curl -L -o %SQLITE_ZIP% %SQLITE_URL%
    powershell -Command "Expand-Archive -Path '%SQLITE_ZIP%' -DestinationPath '%SQLITE_DIR%'"
    move %SQLITE_DIR%\sqlite3.exe . >nul
    del /q %SQLITE_ZIP%
    rmdir /s /q %SQLITE_DIR%
    echo [INFO] sqlite3 安装完成。
) else (
    echo [INFO] 已检测到 sqlite3，跳过安装。
)

::------------------------------------------
:: [2] 创建虚拟环境（如果不存在）
::------------------------------------------
if not exist %VENV_DIR%\Scripts\activate.bat (
    echo [INFO] 正在创建 Python 虚拟环境...
    python -m venv %VENV_DIR%
) else (
    echo [INFO] 虚拟环境已存在，跳过创建。
)

::------------------------------------------
:: [3] 激活虚拟环境
::------------------------------------------
call %VENV_DIR%\Scripts\activate.bat

::------------------------------------------
:: [4] 安装依赖
::------------------------------------------
echo [INFO] 正在安装后端依赖（requirements.txt）...
python -m pip install --upgrade pip
pip install -r requirements.txt

::------------------------------------------
:: [5] 启动后端服务
::------------------------------------------
echo [INFO] 启动 uvicorn 开发服务器...
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

endlocal
