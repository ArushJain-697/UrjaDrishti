from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from src.services.forecastService import get_forecast, get_intraday_forecast

router = APIRouter()

class ForecastRequest(BaseModel):
    plant_id: str
    hours_of_actuals: Optional[int] = 0

class IntradayRequest(BaseModel):
    plant_id: str
    actuals: List[float]

@router.post("/")
def forecast(req: ForecastRequest):
    return get_forecast(req.plant_id, req.hours_of_actuals)

@router.post("/intraday")
def intraday(req: IntradayRequest):
    return get_intraday_forecast(req.plant_id, req.actuals)