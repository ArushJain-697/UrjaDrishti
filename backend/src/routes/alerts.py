import math
from typing import List

from fastapi import APIRouter, Request
from pydantic import BaseModel, field_validator, model_validator

from src.constants import VALID_PLANT_IDS
from src.rate_limit import limiter
from src.services.alertService import get_alerts

router = APIRouter()


class AlertRequest(BaseModel):
    plant_id: str
    p50: List[float]
    hours: List[int]

    @field_validator("plant_id")
    @classmethod
    def plant_id_must_be_valid(cls, v: str) -> str:
        if v not in VALID_PLANT_IDS:
            raise ValueError("Invalid plant_id")
        return v

    @field_validator("p50")
    @classmethod
    def p50_must_be_reasonable(cls, v: List[float]) -> List[float]:
        if len(v) < 1 or len(v) > 48:
            raise ValueError("p50 must have length between 1 and 48")
        for x in v:
            if x < 0 or not math.isfinite(x):
                raise ValueError("p50 values must be non-negative finite numbers")
        return v

    @field_validator("hours")
    @classmethod
    def hours_range(cls, v: List[int]) -> List[int]:
        for h in v:
            if h < 0 or h > 23:
                raise ValueError("each hour must be between 0 and 23")
        return v

    @model_validator(mode="after")
    def lengths_must_match(self):
        if len(self.p50) != len(self.hours):
            raise ValueError("hours length must match p50 length")
        return self


@router.post("/")
@limiter.limit("30/minute")
def alerts_endpoint(request: Request, req: AlertRequest):
    return get_alerts(req.plant_id, req.p50, req.hours)
