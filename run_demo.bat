@echo off
REM NETRA-DR — Phase 1 Prototype Demo Launcher (Windows)
REM Usage: run_demo.bat

cd /d "%~dp0"

echo.
echo ============================================================
echo   NETRA-DR Phase 1 Prototype Demo Launcher
echo ============================================================
echo.

set PYTHON_EXEC=python
if exist "external\EyeQ\.venv\Scripts\python.exe" (
    set PYTHON_EXEC=external\EyeQ\.venv\Scripts\python.exe
    echo [*] Using EyeQ Python environment: %PYTHON_EXEC%
)

echo [1/2] Verifying Python environment...
%PYTHON_EXEC% -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARN] Dependency check encountered a notice, proceeding...
)

echo.
echo [2/2] Starting NETRA-DR demo server...
echo       Open your browser at: http://127.0.0.1:5000
echo       Press Ctrl+C to stop.
echo.

%PYTHON_EXEC% app/app.py
