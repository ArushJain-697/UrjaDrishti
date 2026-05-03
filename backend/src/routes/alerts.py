from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from src.services.alertService import get_alerts

router = APIRouter()

class AlertRequest(BaseModel):
    plant_id: str
    p50: List[float]
    hours: List[int]

@router.post("/")
def alerts(req: AlertRequest):
    return get_alerts(req.plant_id, req.p50, req.hours)