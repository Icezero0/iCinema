@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo [INFO] Checking Node.js...
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install from https://nodejs.org
    exit /b 1
)

REM ---- Check Node major version (>=18) ----
for /f "tokens=1 delims=." %%v in ('node -v') do (
    set NODE_MAJOR=%%v
)
set NODE_MAJOR=%NODE_MAJOR:v=%

if %NODE_MAJOR% LSS 18 (
    echo [ERROR] Node.js >= 18 is required. Current: %NODE_MAJOR%
    exit /b 1
)

REM ---- Check node_modules and lockfile ----
if not exist node_modules (
    echo [INFO] node_modules not found, installing dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        exit /b 1
    )
) else if not exist package-lock.json (
    echo [WARN] package-lock.json not found, reinstalling dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        exit /b 1
    )
) else (
    echo [INFO] Dependencies already installed.
)

REM ---- Start dev server ----
echo [INFO] Starting Vite dev server...
REM --host allows access from LAN / mobile devices
call npm run dev -- --host

endlocal
