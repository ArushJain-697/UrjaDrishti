#!/bin/bash

echo "=========================================="
echo "   Starting UrjaDrishti Forecasting System"
echo "=========================================="

# ============================================
# 1. BACKEND SETUP
# ============================================
echo ""
echo "[1/5] Setting up backend environment..."

cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q

echo "Backend environment ready."

# ============================================
# 2. RUN PERSON 2'S MODEL (includes Person 3's explainability)
# ============================================
echo ""
echo "[2/5] Running Person 2's forecasting model..."
echo "       (This also generates Person 3's explanations)"

python -m src.ml.forecasting.main

echo "Person 2 + Person 3 pipeline completed."

# ============================================
# 3. RUN PERSON 4'S EVALUATION
# ============================================
echo ""
echo "[3/5] Running Person 4's evaluation scripts..."

python -m src.ml.evaluation.test_baselines
python -m src.ml.evaluation.test_harness
python -m src.ml.evaluation.run_stress_evaluation
python -m src.ml.evaluation.run_day5_report

echo "Person 4 evaluation completed."

# ============================================
# 4. START FRONTEND
# ============================================
echo ""
echo "[4/5] Starting frontend..."

cd ../frontend
npm install -q
npm run dev &

FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "   SYSTEM READY"
echo "=========================================="
echo ""
echo "Dashboard: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop everything"
echo ""

trap "kill $FRONTEND_PID" EXIT
wait