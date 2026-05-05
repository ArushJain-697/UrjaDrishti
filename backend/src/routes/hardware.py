"""
GET /api/hardware_check/
POST /api/hardware_check/plant  (single plant)

Returns hardware anomaly status for all plants (fleet-level) or one plant.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from src.rate_limit import limiter
from src.services.hardwareService import detect_hardware_issues, detect_fleet_anomalies

router = APIRouter()


class PlantHardwareRequest(BaseModel):
    plant_id: str
    actuals: list[float]
    p10_forecast: list[float]
    violation_threshold: int = 7


class FleetHardwareRequest(BaseModel):
    plant_data: dict   # {plant_id: {actuals: [...], p10: [...]}}
    violation_threshold: int = 7


@router.post("/plant")
@limiter.limit("300/minute")
def check_plant_hardware(request: Request, body: PlantHardwareRequest):
    """Detect hardware anomalies for a single plant."""
    return detect_hardware_issues(
        plant_id=body.plant_id,
        actuals=body.actuals,
        p10_forecast=body.p10_forecast,
        violation_threshold=body.violation_threshold,
    )


@router.post("/fleet")
@limiter.limit("300/minute")
def check_fleet_hardware(request: Request, body: FleetHardwareRequest):
    """Detect hardware anomalies across the full fleet."""
    return detect_fleet_anomalies(
        plant_data=body.plant_data,
        violation_threshold=body.violation_threshold,
    )
