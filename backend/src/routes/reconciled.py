from fastapi import APIRouter, Request

from src.rate_limit import limiter
from src.services.reconciledService import get_reconciled

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
def reconciled(request: Request):
    return get_reconciled()
