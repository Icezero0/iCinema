@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo [INFO] Checking Node.js...

REM ---- Verify node executable ----
node -v >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found.
    echo Please install Node.js from:
    echo https://nodejs.org
    exit /b 1
)

REM ---- Get Node major version ----
for /f "tokens=1 delims=." %%v in ('node -v') do (
    set NODE_MAJOR=%%v
)

set NODE_MAJOR=!NODE_MAJOR:v=!

if not defined NODE_MAJOR (
    echo [ERROR] Unable to detect Node.js version.
    exit /b 1
)

REM ---- Enforce version ----
if !NODE_MAJOR! LSS 18 (
    echo.
    echo ==========================================
    echo   Node.js version too old
    echo ==========================================
    echo Required: Node.js ^>= 18
    echo Current : !NODE_MAJOR!
    echo.
    echo Download: https://nodejs.org
    echo.
    start "" https://nodejs.org
    exit /b 1
)

echo [INFO] Node.js version OK: !NODE_MAJOR!

REM ---- Install dependencies safely ----
echo [INFO] Installing dependencies...

if exist package-lock.json (
    call npm ci
) else (
    call npm install
)

if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    exit /b 1
)

echo [INFO] Frontend dependencies are ready.
echo [INFO] Run run_frontend.bat to start the Vite dev server.

endlocal
