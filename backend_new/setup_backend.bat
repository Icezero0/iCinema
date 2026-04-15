@echo off
setlocal

echo ==========================================
echo   FastAPI Backend Setup Script
echo ==========================================
echo.

echo [INFO] Current directory: %cd%
echo.

REM -------------------------------------------------
REM 1. Check Python
REM -------------------------------------------------
python --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found.
    echo.
    echo Please install Python 3.12 or newer:
    echo https://www.python.org/downloads/windows/
    pause
    exit /b 1
)

echo [INFO] Python detected
python --version
echo.

REM -------------------------------------------------
REM 2. Check requirements.txt
REM -------------------------------------------------
if not exist requirements.txt (
    echo [ERROR] requirements.txt was not found
    pause
    exit /b 1
)

REM -------------------------------------------------
REM 3. Initialize .env
REM -------------------------------------------------
if not exist .env (
    if exist .env.development (
        echo [INFO] .env not found, copying from .env.development...
        copy /Y .env.development .env >nul
        if errorlevel 1 (
            echo [ERROR] Failed to initialize .env
            pause
            exit /b 1
        )
        echo [INFO] .env created
    ) else (
        echo [WARN] Neither .env nor .env.development was found
    )
) else (
    echo [INFO] .env already exists, skip initialization
)

echo.

REM -------------------------------------------------
REM 4. Create virtual environment
REM -------------------------------------------------
set "VENV_DIR=venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo [INFO] Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo [INFO] Virtual environment already exists
)

echo.

REM -------------------------------------------------
REM 5. Use Python from venv
REM -------------------------------------------------
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Python in virtual environment was not found: %VENV_PYTHON%
    pause
    exit /b 1
)

echo [INFO] Using Python from virtual environment:
"%VENV_PYTHON%" --version
echo.

REM -------------------------------------------------
REM 6. Install base dependencies
REM -------------------------------------------------
echo [INFO] Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip
    pause
    exit /b 1
)

echo.
echo [INFO] Installing base backend dependencies...
"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [INFO] Running Alembic upgrade head...
"%VENV_PYTHON%" -m alembic upgrade head
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to upgrade database schema with Alembic
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   Setup Complete
echo ==========================================
echo.
echo [INFO] Database schema has been upgraded to the latest Alembic revision.
echo [INFO] Startup will run Alembic again as a safe fallback.
echo.
echo [INFO] Start backend: run_backend.bat
echo [INFO] Run tests: test_backend.bat

endlocal
