import numpy as np


def _mock_alerts(plant_id: str, p50: list, hours: list):
    """Fallback mock alerts if ml_generate_alerts fails"""
    alerts = [
        {
            "hour": 10,
            "message": "☁️ Heavy cloud cover limiting generation at 10:00 — cloud modification factor is the primary negative driver (~25.4% reduction)",
            "type": "warning",
            "template": "high_cloud_cover",
            "top_drivers": [
                {"feature": "CMF", "shap_value": -0.254},
                {"feature": "hour_sin", "shap_value": 0.082},
                {"feature": "temperature", "shap_value": -0.041}
            ]
        },
        {
            "hour": 13,
            "message": "🔆 Peak solar generation window (midday) at 13:00 — time-of-day positioning drives strong output (~18.2% boost)",
            "type": "success",
            "template": "peak_solar_hours",
            "top_drivers": [
                {"feature": "hour_sin", "shap_value": 0.182},
                {"feature": "CMF", "shap_value": 0.125},
                {"feature": "temperature", "shap_value": -0.030}
            ]
        },
        {
            "hour": 17,
            "message": "⚠️ High atmospheric uncertainty at 17:00 — wider confidence intervals recommended (~12.5% impact)",
            "type": "info",
            "template": "high_uncertainty",
            "top_drivers": [
                {"feature": "nwp_spread", "shap_value": -0.125},
                {"feature": "hour_sin", "shap_value": -0.091},
                {"feature": "CMF", "shap_value": -0.022}
            ]
        }
    ]
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