#!/bin/bash
echo "Starting KREDL Forecasting System..."

cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q
uvicorn src.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend running on http://localhost:8000"

cd ../frontend
npm install -q
npm run dev &
FRONTEND_PID=$!
echo "Frontend running on http://localhost:5173"

echo ""
echo "System ready."
echo "Dashboard: http://localhost:5173"
echo "API docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop everything"

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait