from fastapi import APIRouter, Request

from src.rate_limit import limiter
from src.services.evaluationService import get_evaluation, get_historical_sample

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
def evaluation(request: Request):
    return get_evaluation()

@router.get("/historical_sample")
@limiter.limit("60/minute")
def historical_sample(request: Request, date: str = "2024-01-15"):
    return get_historical_sample(date)
