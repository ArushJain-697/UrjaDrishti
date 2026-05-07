#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
VENV_DIR="${BACKEND_DIR}/venv"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "${FRONTEND_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: Required command not found: $1"
    exit 1
  fi
}

ensure_dir() {
  if [[ ! -d "$1" ]]; then
    echo "ERROR: Required directory not found: $1"
    exit 1
  fi
}

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi
  echo "ERROR: Python not found. Install Python 3.10+ and retry."
  exit 1
}

echo "=========================================="
echo "   Starting UrjaDrishti Forecasting System"
echo "=========================================="

require_cmd npm
PYTHON_BIN="$(find_python)"
ensure_dir "${BACKEND_DIR}"
ensure_dir "${FRONTEND_DIR}"

echo ""
echo "[1/5] Setting up backend environment..."
cd "${BACKEND_DIR}"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Creating virtual environment..."
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip >/dev/null 2>&1 || true
python -m pip install -r requirements.txt
echo "Backend environment ready."

echo ""
echo "[2/5] Generating forecasting models..."
PYTHONPATH="${BACKEND_DIR}" python -m src.ml.forecasting.main

echo ""
echo "[3/5] Running evaluation scripts..."
PYTHONPATH="${BACKEND_DIR}" python -m src.ml.evaluation.test_baselines
PYTHONPATH="${BACKEND_DIR}" python -m src.ml.evaluation.test_harness
PYTHONPATH="${BACKEND_DIR}" python -m src.ml.evaluation.run_stress_evaluation
PYTHONPATH="${BACKEND_DIR}" python -m src.ml.evaluation.run_day5_report
echo "Evaluation completed."

echo ""
echo "[4/5] Starting backend..."
uvicorn src.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend running on http://localhost:8000"

echo ""
echo "[5/5] Starting frontend..."
cd "${FRONTEND_DIR}"
npm install
npm run dev &
FRONTEND_PID=$!
echo "Frontend running on http://localhost:5173"

echo ""
echo "=========================================="
echo "   SYSTEM READY"
echo "=========================================="
echo ""
echo "Dashboard: http://localhost:5173"
echo "API docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop everything"
echo ""

wait "${FRONTEND_PID}"
wait "${BACKEND_PID}"