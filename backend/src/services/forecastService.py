import numpy as np

from src.ml.forecasting.predict import get_forecast as ml_forecast
from src.ml.forecasting.predict import get_intraday_forecast as ml_intraday

SOLAR_PLANTS = ['PVG_S1', 'PVG_S2', 'MIX_S1']
WIND_PLANTS  = ['GAD_W1', 'GAD_W2', 'MIX_W1']

def _mock_forecast(plant_id: str, narrow: bool = False):
    hours = list(range(24))
    is_solar = plant_id in SOLAR_PLANTS
    spread = 10 if narrow else 15

    if is_solar:
        p50 = [
            round(max(0, 80 * np.sin(np.pi * (h - 6) / 12) + np.random.uniform(-5, 5)), 2)
            for h in hours
        ]
    else:
        p50 = [round(max(0, 40 + np.random.uniform(-15, 15)), 2) for h in hours]

    p10 = [round(max(0, v - spread - np.random.uniform(0, 5)), 2) for v in p50]
    p90 = [round(v + spread + np.random.uniform(0, 5), 2) for v in p50]

    return {"plant_id": plant_id, "hours": hours, "p50": p50, "p10": p10, "p90": p90}


def get_forecast(plant_id: str, hours_of_actuals: int = 0):
    try:
        return ml_forecast(plant_id, hours_of_actuals)
    except Exception as e:
        print(f"Model error: {e} — falling back to mock")
        return _mock_forecast(plant_id)


def get_intraday_forecast(plant_id: str, actuals: list):
    try:
        return ml_intraday(plant_id, actuals)
    except Exception as e:
        print(f"Intraday model error: {e} — falling back to mock")
        return _mock_forecast(plant_id, narrow=True)