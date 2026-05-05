"""
POST /api/calibration/plant   — single plant quantile audit
POST /api/calibration/system  — fleet-wide calibration audit
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
from src.rate_limit import limiter
from src.services.calibrationService import audit_plant_quantiles, audit_system_calibration

router = APIRouter()


class PlantCalibrationRequest(BaseModel):
    plant_id: str
    actuals: list[float]
    p10: list[float]
    p50: list[float]
    p90: list[float]


class SystemCalibrationRequest(BaseModel):
    plant_data: dict   # {plant_id: {actuals, p10, p50, p90}}
    quantile_levels: Optional[list[float]] = None


@router.post("/plant")
@limiter.limit("300/minute")
def audit_plant(request: Request, body: PlantCalibrationRequest):
    """Audit quantile calibration for a single plant."""
    return audit_plant_quantiles(
        plant_id=body.plant_id,
        actuals=body.actuals,
        p10=body.p10,
        p50=body.p50,
        p90=body.p90,
    )


@router.post("/system")
@limiter.limit("300/minute")
def audit_system(request: Request, body: SystemCalibrationRequest):
    """Audit quantile calibration for the full fleet."""
    return audit_system_calibration(
        plant_data=body.plant_data,
        quantile_levels=body.quantile_levels,
    )
