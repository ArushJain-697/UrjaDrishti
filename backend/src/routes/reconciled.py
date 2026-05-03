from fastapi import APIRouter
from src.services.reconciledService import get_reconciled

router = APIRouter()

@router.get("/")
def reconciled():
    return get_reconciled()