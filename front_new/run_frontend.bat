@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo [INFO] Checking Node.js...

node -v >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found.
    echo Please install Node.js from:
    echo https://nodejs.org
    exit /b 1
)

for /f "tokens=1 delims=." %%v in ('node -v') do (
    set NODE_MAJOR=%%v
)

set NODE_MAJOR=!NODE_MAJOR:v=!

if not defined NODE_MAJOR (
    echo [ERROR] Unable to detect Node.js version.
    exit /b 1
)

if !NODE_MAJOR! LSS 18 (
    echo [ERROR] Node.js ^>= 18 is required. Current: !NODE_MAJOR!
    exit /b 1
)

if not exist node_modules (
    echo [ERROR] Dependencies are not installed.
    echo Please run setup_frontend.bat first.
    exit /b 1
)

echo [INFO] Starting Vite dev server...
call npm run dev -- --host

endlocal
