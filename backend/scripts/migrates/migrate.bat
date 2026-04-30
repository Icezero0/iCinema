@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "BACKEND_ROOT=%%~fI"
set "VENV_PYTHON=%BACKEND_ROOT%\venv\Scripts\python.exe"

if exist "%VENV_PYTHON%" (
    set "PYTHON=%VENV_PYTHON%"
) else (
    set "PYTHON=python"
)

cd /d "%BACKEND_ROOT%"
"%PYTHON%" "scripts\migrates\migrate.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Migration failed with exit code %EXIT_CODE%.
    exit /b %EXIT_CODE%
)

echo.
echo === Stamping Alembic baseline ===
set "DEBUG=false"
"%PYTHON%" -m alembic -c "%BACKEND_ROOT%\alembic.ini" stamp head
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Alembic stamp failed with exit code %EXIT_CODE%.
    exit /b %EXIT_CODE%
)

echo.
echo Migration completed successfully.
exit /b 0
