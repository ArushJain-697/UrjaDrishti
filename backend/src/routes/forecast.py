import math
from typing import List

from fastapi import APIRouter, Request
from pydantic import BaseModel, field_validator

from src.constants import VALID_PLANT_IDS
from src.rate_limit import limiter
from src.services.forecastService import get_forecast, get_intraday_forecast

router = APIRouter()


class ForecastRequest(BaseModel):
    plant_id: str
    hours_of_actuals: int = 0

    @field_validator("plant_id")
    @classmethod
    def plant_id_must_be_valid(cls, v: str) -> str:
        if v not in VALID_PLANT_IDS:
            raise ValueError("Invalid plant_id")
        return v

    @field_validator("hours_of_actuals")
    @classmethod
    def hours_must_be_reasonable(cls, v: int) -> int:
        if v < 0 or v > 23:
            raise ValueError("hours_of_actuals must be between 0 and 23")
        return v


class IntradayRequest(BaseModel):
    plant_id: str
    actuals: List[float]

    @field_validator("plant_id")
    @classmethod
    def plant_id_must_be_valid(cls, v: str) -> str:
        if v not in VALID_PLANT_IDS:
            raise ValueError("Invalid plant_id")
        return v

    @field_validator("actuals")
    @classmethod
    def actuals_must_be_reasonable(cls, v: List[float]) -> List[float]:
        if len(v) < 1 or len(v) > 24:
            raise ValueError("actuals must have length between 1 and 24")
        for x in v:
            if x < 0 or not math.isfinite(x):
                raise ValueError("actuals must be non-negative finite numbers")
        return v


@router.post("/")
@limiter.limit("300/minute")
def forecast_endpoint(request: Request, req: ForecastRequest):
    return get_forecast(req.plant_id, req.hours_of_actuals)


@router.post("/intraday")
@limiter.limit("300/minute")
def intraday_endpoint(request: Request, req: IntradayRequest):
    return get_intraday_forecast(req.plant_id, req.actuals)
