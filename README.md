# UrjaDrishti# KREDL / KSPDCL — AI Renewable Generation Forecasting

AI-based solar and wind generation forecasting for Karnataka.
Predicts plant-level and cluster-level output with uncertainty ranges
and plain-language explainability.

## Quick Start

git clone <repo>
cd kredl-forecasting
bash start.sh

Dashboard: http://localhost:5173  
API docs:  http://localhost:8000/docs

## Setup (manual)

### Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

### Frontend
cd frontend
npm install
npm run dev

## Data

Feature matrix CSV shared via Google Drive: [LINK HERE]
Place it at: data/feature_matrix_final.csv

## Team

Person 1 — Data & Physics: data/
Person 2 — Forecasting Model: backend/src/ml/forecasting/
Person 3 — Explainability & Reconciliation: backend/src/ml/explainability/
Person 4 — Evaluation: backend/src/ml/evaluation/
Person 5 — Backend API & Frontend: backend/src/ + frontend/

## API Documentation

FastAPI auto-generates docs at http://localhost:8000/docs
Test all endpoints interactively there.

## Deployment

Production deployment uses HTTPS with TLS termination at the nginx reverse proxy layer — all traffic between the dashboard and the forecasting API is encrypted in transit.

### Security (backend)

- Set `API_KEY` in the backend environment (see `backend/.env.example`). The frontend must send the same value in `X-API-Key` (see `frontend/.env.example` / `VITE_API_KEY`).
- Request audit trail: `backend/logs/api_access.log` (created at runtime).
- Rate limits: forecasting and alert POST routes default to 30 requests/minute per client IP; evaluation and reconciled GET routes to 60/minute.