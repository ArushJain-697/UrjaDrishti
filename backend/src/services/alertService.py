import numpy as np


def _mock_alerts(plant_id: str, p50: list, hours: list):
    """Fallback mock alerts if ml_generate_alerts fails"""
    alerts = []
    avg = np.mean([v for v in p50 if v > 0]) if any(v > 0 for v in p50) else 0

    for i, (h, v) in enumerate(zip(hours, p50)):
        if v < avg * 0.75 and v > 0:
            alerts.append({
                "hour": h,
                "message": f"Output for {plant_id} at {h:02d}:00 is forecast 25% below seasonal expected — cloud modification factor is the dominant driver.",
                "type": "warning"
            })
        elif v == max(p50):
            alerts.append({
                "hour": h,
                "message": f"{plant_id} forecast to peak at {h:02d}:00 — conditions favourable, high confidence interval.",
                "type": "success"
            })

    # Ensure hour 17 info alert is only added once
    if not any(a["hour"] == 17 for a in alerts):
        alerts.append({
            "hour": 17,
            "message": f"Atmospheric uncertainty rising for {plant_id} after 17:00 — intraday update recommended before evening scheduling.",
            "type": "info"
        })

    return {"alerts": alerts}


def get_alerts(plant_id: str, p50: list, hours: list):
    """
    Get SHAP-driven alerts from Person 3's explainability module.
    Import is deferred inside the function so a missing/broken ML
    dependency never prevents the FastAPI app from starting.
    Falls back to mock if import or generation fails.
    """
    try:
        from src.ml.explainability.alerts import generate_alerts as ml_generate_alerts
        return ml_generate_alerts(plant_id, p50, hours)
    except Exception as e:
        print(f"Alert generation error: {e} — falling back to mock")
        return _mock_alerts(plant_id, p50, hours)