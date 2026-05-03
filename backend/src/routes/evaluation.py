from fastapi import APIRouter, Request

from src.rate_limit import limiter
from src.services.evaluationService import get_evaluation

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
def evaluation(request: Request):
    return get_evaluation()
