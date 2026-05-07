"""
Service layer for Quantile Calibration Audit
Exposes calibration verification through API
"""

from src.ml.explainability.quantile_audit import (
    QuantileCalibrationAudit, 
    audit_multi_plant_calibration,
    generate_reliability_diagram_analysis
)
import numpy as np

MOCK_CALIBRATION_RESULT = {
    "timestamp": "2026-05-05T12:00:00",
    "plants": {
        "PVG_S1": {
            "calibration_results": {
                0.1: {"nominal_quantile": 0.1, "observed_coverage": 0.12, "deviation": 0.02},
                0.5: {"nominal_quantile": 0.5, "observed_coverage": 0.50, "deviation": 0.00},
                0.9: {"nominal_quantile": 0.9, "observed_coverage": 0.88, "deviation": 0.02}
            },
            "is_calibrated": True,
            "calibration_status": "✓ WELL-CALIBRATED"
        },
        "PVG_S2": {
            "calibration_results": {
                0.1: {"nominal_quantile": 0.1, "observed_coverage": 0.11, "deviation": 0.01},
                0.5: {"nominal_quantile": 0.5, "observed_coverage": 0.49, "deviation": 0.01},
                0.9: {"nominal_quantile": 0.9, "observed_coverage": 0.91, "deviation": 0.01}
            },
            "is_calibrated": True,
            "calibration_status": "✓ WELL-CALIBRATED"
        },
        "MIX_S1": {
            "calibration_results": {
                0.1: {"nominal_quantile": 0.1, "observed_coverage": 0.13, "deviation": 0.03},
                0.5: {"nominal_quantile": 0.5, "observed_coverage": 0.52, "deviation": 0.02},
                0.9: {"nominal_quantile": 0.9, "observed_coverage": 0.87, "deviation": 0.03}
            },
            "is_calibrated": True,
            "calibration_status": "✓ WELL-CALIBRATED"
        },
        "GAD_W1": {
            "calibration_results": {
                0.1: {"nominal_quantile": 0.1, "observed_coverage": 0.09, "deviation": 0.01},
                0.5: {"nominal_quantile": 0.5, "observed_coverage": 0.51, "deviation": 0.01},
                0.9: {"nominal_quantile": 0.9, "observed_coverage": 0.92, "deviation": 0.02}
            },
            "is_calibrated": True,
            "calibration_status": "✓ WELL-CALIBRATED"
        },
        "GAD_W2": {
            "calibration_results": {
                0.1: {"nominal_quantile": 0.1, "observed_coverage": 0.10, "deviation": 0.00},
                0.5: {"nominal_quantile": 0.5, "observed_coverage": 0.50, "deviation": 0.00},
                0.9: {"nominal_quantile": 0.9, "observed_coverage": 0.90, "deviation": 0.00}
            },
            "is_calibrated": True,
            "calibration_status": "✓ WELL-CALIBRATED"
        },
        "MIX_W1": {
            "calibration_results": {
                0.1: {"nominal_quantile": 0.1, "observed_coverage": 0.12, "deviation": 0.02},
                0.5: {"nominal_quantile": 0.5, "observed_coverage": 0.48, "deviation": 0.02},
                0.9: {"nominal_quantile": 0.9, "observed_coverage": 0.89, "deviation": 0.01}
            },
            "is_calibrated": True,
            "calibration_status": "✓ WELL-CALIBRATED"
        }
    },
    "all_calibrated": True,
    "status": "✓ SYSTEM CALIBRATED"
}

def audit_plant_quantiles(plant_id: str, actuals: list, p10: list, p50: list, p90: list):
    """
    Audit quantile calibration for a single plant.
    
    Args:
        plant_id: Plant identifier
        actuals: Actual generation values
        p10, p50, p90: Quantile forecasts
    
    Returns:
        Calibration audit result showing per-quantile coverage
    """
    try:
        auditor = QuantileCalibrationAudit(verbose=False)
        
        y_pred_quantiles = {
            0.1: np.array(p10),
            0.5: np.array(p50),
            0.9: np.array(p90)
        }
        
        result = auditor.audit_calibration(np.array(actuals), y_pred_quantiles)
        
        return {
            "status": "success",
            "plant_id": plant_id,
            "result": result
        }
    except Exception as e:
        print(f"Quantile audit error for {plant_id}: {e} — falling back to mock")
        return {
            "status": "error",
            "error": str(e),
            "plant_id": plant_id,
            "result": MOCK_CALIBRATION_RESULT.get("plants", {}).get("PVG_S1", {})
        }


def audit_system_calibration(plant_data: dict, quantile_levels: list = None):
    """
    Audit quantile calibration across all plants.
    
    Args:
        plant_data: {plant_id: {"actuals": [...], "p10": [...], "p50": [...], "p90": [...]}, ...}
        quantile_levels: List of quantiles to audit (default: [0.1, 0.5, 0.9])
    
    Returns:
        System-level calibration audit with reliability diagram data
    """
    try:
        if not plant_data:
            return {
                "status": "success",
                "result": MOCK_CALIBRATION_RESULT,
                "analysis": "Returning mock calibration analysis because no plant data was provided",
                "note": "Returning mock data because no plant data was provided"
            }
        if quantile_levels is None:
            quantile_levels = [0.1, 0.5, 0.9]
        
        # Convert to numpy arrays for all values
        plant_data_arrays = {}
        for plant_id, data in plant_data.items():
            plant_data_arrays[plant_id] = {
                'actuals': np.array(data.get('actuals', [])),
                'p10': np.array(data.get('p10', [])),
                'p25': np.array(data.get('p25', [])),
                'p50': np.array(data.get('p50', [])),
                'p75': np.array(data.get('p75', [])),
                'p90': np.array(data.get('p90', []))
            }
        
        result = audit_multi_plant_calibration(plant_data_arrays, quantile_levels)
        
        # Add interpretation
        analysis = generate_reliability_diagram_analysis(result)
        
        return {
            "status": "success",
            "result": result,
            "analysis": analysis
        }
    except Exception as e:
        print(f"System calibration audit error: {e} — falling back to mock")
        return {
            "status": "error",
            "error": str(e),
            "result": MOCK_CALIBRATION_RESULT,
            "analysis": "Error computing analysis"
        }


def get_reliability_diagram_data(audit_result: dict):
    """
    Extract reliability diagram data (for plotting).
    
    Returns:
        List of (nominal, observed) points for each plant and quantile
    """
    diagram_data = {}
    
    for plant_id, plant_result in audit_result.get('plants', {}).items():
        diagram_data[plant_id] = plant_result.get('reliability_diagram', {})
    
    return {
        "status": "success",
        "diagram_data": diagram_data,
        "interpretation": "Perfect calibration: observed = nominal (45-degree line in plot)"
    }


__all__ = ['audit_plant_quantiles', 'audit_system_calibration', 'get_reliability_diagram_data']
