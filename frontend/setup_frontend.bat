@echo off
chcp 65001 >nul
setlocal

echo [INFO] 正在检查 Node.js 是否已安装...
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] 未检测到 Node.js，请先从 https://nodejs.org 安装。
    exit /b 1
)
echo [INFO] 安装前端依赖...
call npm install
echo [INFO] npm install 执行完毕

echo [INFO] 启动 Vite 开发服务器（npm run dev）...
npm run dev -- --host

endlocal
