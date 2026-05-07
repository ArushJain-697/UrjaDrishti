"""
Service layer for Hardware Anomaly Detection
Exposes hardware diagnostics through API
"""

from src.ml.explainability.hardware_diagnostics import HardwareAnomalyDetector, detect_hardware_anomalies_batch
import numpy as np

MOCK_ANOMALY_RESULT = {
    "timestamp": "2026-05-05T12:00:00",
    "plants": {
        "PVG_S1": {"anomaly": False, "severity": "none", "recommendation": "✓ No action required."},
        "PVG_S2": {"anomaly": False, "severity": "none", "recommendation": "✓ No action required."},
        "MIX_S1": {"anomaly": False, "severity": "none", "recommendation": "✓ No action required."},
        "GAD_W1": {"anomaly": False, "severity": "none", "recommendation": "✓ No action required."},
        "GAD_W2": {"anomaly": False, "severity": "none", "recommendation": "✓ No action required."},
        "MIX_W1": {"anomaly": False, "severity": "none", "recommendation": "✓ No action required."}
    },
    "anomalies_detected": [],
    "system_status": "✓ HEALTHY"
}

def detect_hardware_issues(plant_id: str, actuals: list, p10_forecast: list, 
                           violation_threshold: int = 7):
    """
    Detect hardware anomalies for a single plant.
    
    Args:
        plant_id: Plant identifier
        actuals: Actual generation values (list or array)
        p10_forecast: P10 forecast values
        violation_threshold: Consecutive hour threshold (default: 7)
    
    Returns:
        Anomaly detection result with severity and recommendation
    """
    try:
        detector = HardwareAnomalyDetector(violation_threshold_hours=violation_threshold)
        result = detector.detect_anomaly(actuals, p10_forecast, plant_id)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        print(f"Hardware anomaly detection error: {e} — falling back to mock")
        return {
            "status": "error",
            "error": str(e),
            "result": MOCK_ANOMALY_RESULT
        }


def detect_fleet_anomalies(plant_data: dict, violation_threshold: int = 7):
    """
    Detect hardware anomalies across all plants.
    
    Args:
        plant_data: {plant_id: {"actuals": [...], "p10": [...]}, ...}
        violation_threshold: Consecutive hour threshold
    
    Returns:
        System-level anomaly report
    """
    try:
        result = detect_hardware_anomalies_batch(plant_data, violation_threshold)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        print(f"Fleet anomaly detection error: {e} — falling back to mock")
        return {
            "status": "error",
            "error": str(e),
            "result": MOCK_ANOMALY_RESULT
        }


__all__ = ['detect_hardware_issues', 'detect_fleet_anomalies']
