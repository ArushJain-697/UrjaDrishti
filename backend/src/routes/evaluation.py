from fastapi import APIRouter
from src.services.evaluationService import get_evaluation

router = APIRouter()

@router.get("/")
def evaluation():
    return get_evaluation()