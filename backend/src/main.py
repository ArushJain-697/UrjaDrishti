from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import forecast, alerts, evaluation, reconciled
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app = FastAPI(title="KREDL Renewable Forecasting API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast.router,     prefix="/api/forecast",    tags=["Forecast"])
app.include_router(alerts.router,       prefix="/api/alerts",      tags=["Alerts"])
app.include_router(evaluation.router,   prefix="/api/evaluation",  tags=["Evaluation"])
app.include_router(reconciled.router,   prefix="/api/reconciled",  tags=["Reconciled"])

@app.get("/")
def root():
    return {"status": "KREDL Forecasting API is running"}