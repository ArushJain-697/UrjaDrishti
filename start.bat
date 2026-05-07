@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo    Starting UrjaDrishti Forecasting System
echo ==========================================

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "PYTHON_BIN="

if not exist "%BACKEND_DIR%\" (
    echo ERROR: Backend directory not found: %BACKEND_DIR%
    exit /b 1
)
if not exist "%FRONTEND_DIR%\" (
    echo ERROR: Frontend directory not found: %FRONTEND_DIR%
    exit /b 1
)

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_BIN=py -3"
)

if not defined PYTHON_BIN (
    where python >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_BIN=python"
    )
)

if not defined PYTHON_BIN (
    echo ERROR: Python was not found in PATH. Install Python 3.10+ and retry.
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo ERROR: npm was not found in PATH. Install Node.js LTS and retry.
    exit /b 1
)

echo.
echo [1/5] Setting up backend environment...
cd /d "%BACKEND_DIR%"

if not exist "venv" (
    echo Creating virtual environment...
    %PYTHON_BIN% -m venv venv
    if errorlevel 1 exit /b 1
)

call venv\Scripts\activate.bat
if errorlevel 1 exit /b 1

%PYTHON_BIN% -m pip install --upgrade pip >nul 2>nul
%PYTHON_BIN% -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Backend environment ready.

echo.
echo [2/5] Generating forecasting models...
set "PYTHONPATH=%BACKEND_DIR%"
%PYTHON_BIN% -m src.ml.forecasting.main
if errorlevel 1 (
    echo ERROR: Model generation failed.
    exit /b 1
)

echo.
echo [3/5] Running evaluation scripts...
%PYTHON_BIN% -m src.ml.evaluation.test_baselines
if errorlevel 1 exit /b 1
%PYTHON_BIN% -m src.ml.evaluation.test_harness
if errorlevel 1 exit /b 1
%PYTHON_BIN% -m src.ml.evaluation.run_stress_evaluation
if errorlevel 1 exit /b 1
%PYTHON_BIN% -m src.ml.evaluation.run_day5_report
if errorlevel 1 exit /b 1
echo Evaluation completed.

echo.
echo [4/5] Starting backend...
start "UrjaDrishti Backend" cmd /k "uvicorn src.main:app --reload --port 8000"

echo.
echo [5/5] Starting frontend...
cd /d "%FRONTEND_DIR%"
npm install
if errorlevel 1 exit /b 1

start "UrjaDrishti Frontend" cmd /k "npm run dev"

echo.
echo ==========================================
echo    SYSTEM READY
echo ==========================================
echo.
echo Dashboard: http://localhost:5173
echo API docs:  http://localhost:8000/docs
echo.
echo You can close this window; processes keep running in separate terminals.
exit /b 0