@echo off
setlocal

set "VENV_PYTHON=venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment was not found. Run setup_backend.bat first.
    pause
    exit /b 1
)

echo [INFO] Starting uvicorn...
"%VENV_PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

endlocal
