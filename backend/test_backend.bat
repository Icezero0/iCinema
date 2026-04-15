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

if /I "%~1"=="--help-tests" (
    echo(Usage:
    echo(  test_backend.bat
    echo(  test_backend.bat tests\api\test_media_api.py
    echo(  test_backend.bat tests\api\test_media_api.py::test_upload_image_returns_public_url
    echo(  test_backend.bat tests\unit\modules\media -k sticker
    echo(
    echo(Notes:
    echo(  - No arguments runs the full test suite
    echo(  - Any other arguments are passed directly to pytest
    endlocal
    exit /b 0
)

echo [INFO] Installing test dependencies...
"%VENV_PYTHON%" -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo [ERROR] Failed to install test dependencies
    pause
    exit /b 1
)

echo.
if "%~1"=="" (
    echo [INFO] Running full pytest suite...
) else (
    echo [INFO] Running pytest with selectors: %*
)
"%VENV_PYTHON%" -m pytest %*

endlocal
