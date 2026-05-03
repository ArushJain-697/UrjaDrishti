import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.auth import verify_api_key
from src.rate_limit import limiter
from src.routes import alerts, evaluation, forecast, reconciled

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "api_access.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

app = FastAPI(title="KREDL Renewable Forecasting API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    host = request.client.host if request.client else "-"
    logging.info("%s %s from %s", request.method, request.url.path, host)
    response = await call_next(request)
    logging.info("Response: %s", response.status_code)
    return response


secured = [Depends(verify_api_key)]

app.include_router(
    forecast.router,
    prefix="/api/forecast",
    tags=["Forecast"],
    dependencies=secured,
)
app.include_router(
    alerts.router,
    prefix="/api/alerts",
    tags=["Alerts"],
    dependencies=secured,
)
app.include_router(
    evaluation.router,
    prefix="/api/evaluation",
    tags=["Evaluation"],
    dependencies=secured,
)
app.include_router(
    reconciled.router,
    prefix="/api/reconciled",
    tags=["Reconciled"],
    dependencies=secured,
)


@app.get("/")
def root():
    return {"status": "KREDL Forecasting API is running"}
