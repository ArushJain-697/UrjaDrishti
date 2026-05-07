@echo off
echo ==========================================
echo    Starting UrjaDrishti Forecasting System
echo ==========================================

REM 1. Backend Setup
echo.
echo [1/5] Setting up backend environment...

cd backend

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo Backend environment ready.

REM 2. Run Person 2's Model (includes Person 3)
echo.
echo [2/5] Running Person 2's forecasting model...
echo        (This also generates Person 3's explanations)

python -m src.ml.forecasting.main

echo Person 2 + Person 3 pipeline completed.

REM 3. Run Person 4's Evaluation
echo.
echo [3/5] Running Person 4's evaluation scripts...

python -m src.ml.evaluation.test_baselines
python -m src.ml.evaluation.test_harness
python -m src.ml.evaluation.run_stress_evaluation
python -m src.ml.evaluation.run_day5_report

echo Person 4 evaluation completed.

REM 4. Start Frontend
echo.
echo [4/5] Starting frontend...

cd ..\frontend
npm install -q
start npm run dev

echo.
echo ==========================================
echo    SYSTEM READY
echo ==========================================
echo.
echo Dashboard: http://localhost:5173
echo.
echo Press any key to stop everything...
pause >nul