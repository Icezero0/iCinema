@echo off
setlocal

set "VENV_PYTHON=venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment was not found. Run setup_backend.bat first.
    pause
    exit /b 1
)

if not exist requirements-dev.txt (
    echo [ERROR] requirements-dev.txt was not found
    pause
    exit /b 1
)

echo [INFO] Installing test dependencies...
"%VENV_PYTHON%" -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo [ERROR] Failed to install test dependencies
    pause
    exit /b 1
)

echo.
echo [INFO] Running pytest...
"%VENV_PYTHON%" -m pytest %*

endlocal
