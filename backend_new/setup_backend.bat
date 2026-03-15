@echo off
chcp 65001 >nul
setlocal

echo ==========================================
echo   FastAPI Backend Setup Script
echo ==========================================
echo.

echo [INFO] 当前目录: %cd%
echo.

:: -------------------------------------------------
:: 1️⃣ 检查 Python 是否安装
:: -------------------------------------------------
python --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] 未检测到 Python 环境。
    echo.
    echo 请安装 Python ^(建议 3.12^)
    echo https://www.python.org/downloads/windows/
    pause
    exit /b 1
)

echo [INFO] Python 已安装
python --version
echo.

:: -------------------------------------------------
:: 2️⃣ 检查 requirements.txt
:: -------------------------------------------------
if not exist requirements.txt (
    echo [ERROR] 未找到 requirements.txt
    pause
    exit /b 1
)

:: -------------------------------------------------
:: 3️⃣ 初始化 .env
:: -------------------------------------------------
if not exist .env (
    if exist .env.development (
        echo [INFO] 未检测到 .env，正在从 .env.development 复制...
        copy /Y .env.development .env >nul
        if errorlevel 1 (
            echo [ERROR] .env 初始化失败
            pause
            exit /b 1
        )
        echo [INFO] 已生成 .env
    ) else (
        echo [WARN] 未找到 .env，也未找到 .env.development
    )
) else (
    echo [INFO] .env 已存在，跳过初始化
)

echo.

:: -------------------------------------------------
:: 4️⃣ 创建虚拟环境
:: -------------------------------------------------
set VENV_DIR=venv

if not exist %VENV_DIR%\Scripts\activate.bat (
    echo [INFO] 创建虚拟环境...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [ERROR] 虚拟环境创建失败
        pause
        exit /b 1
    )
) else (
    echo [INFO] 虚拟环境已存在
)

echo.

:: -------------------------------------------------
:: 5️⃣ 激活虚拟环境
:: -------------------------------------------------
call %VENV_DIR%\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] 虚拟环境激活失败
    pause
    exit /b 1
)

:: -------------------------------------------------
:: 6️⃣ 安装依赖
:: -------------------------------------------------
echo [INFO] 升级 pip...
python -m pip install --upgrade pip

echo.
echo [INFO] 安装依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] 依赖安装失败
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   Setup 完成
echo ==========================================
echo.

:: -------------------------------------------------
:: 7️⃣ 启动服务
:: -------------------------------------------------
echo [INFO] 启动 uvicorn...
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

endlocal