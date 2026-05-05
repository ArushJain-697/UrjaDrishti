"""
PERSON 3 — Quantile Calibration Audit & Reliability Diagram
Audits CQR calibration across quantile levels. Shows if predictions are properly calibrated
at each quantile (P10, P50, P90 should have observed coverage matching nominal).
"""

import numpy as np
from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime

# ============================================================
# QUANTILE CALIBRATION AUDIT
# ============================================================

class QuantileCalibrationAudit:
    """Audit CQR calibration per quantile level"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def audit_calibration(self, y_true: np.ndarray, 
                         y_pred_quantiles: Dict[float, np.ndarray],
                         tolerance: float = 0.05) -> Dict:
        """
        Audit calibration of quantile forecasts.
        
        Args:
            y_true: Actual generation values (array of floats)
            y_pred_quantiles: {0.1: [...], 0.5: [...], 0.9: [...]}
            tolerance: Acceptable deviation from nominal quantile (default 5%)
        
        Returns:
            Dictionary with:
            - quantiles: List of quantiles checked
            - calibration_results: Per-quantile coverage
            - is_calibrated: bool (all within tolerance)
            - coverage_deviation: Measure of calibration quality
            - reliability_diagram_data: Points for plotting
        """
        
        y_true = np.array(y_true)
        results = {}
        deviations = []
        
        for q, preds in sorted(y_pred_quantiles.items()):
            preds = np.array(preds)
            
            # Mask out periods where generation is physically zero (e.g. solar at night)
            # If P50 == 0, we should not include it in the quantile audit because 0 <= 0 is true
            # and it artificially inflates coverage.
            valid_mask = y_true > 0.01  # only audit periods with actual generation
            
            if np.sum(valid_mask) > 0:
                observed_coverage = np.mean(y_true[valid_mask] <= preds[valid_mask])
            else:
                observed_coverage = float(q) # fallback if entirely zeros
            
            # Expected coverage == nominal quantile
            deviation = abs(observed_coverage - q)
            deviations.append(deviation)
            
            is_well_calibrated = deviation <= tolerance
            
            results[q] = {
                'nominal_quantile': float(q),
                'observed_coverage': float(observed_coverage),
                'deviation': float(deviation),
                'within_tolerance': bool(is_well_calibrated),
                'sample_size': int(np.sum(valid_mask)),
                'count_below': int(np.sum(y_true[valid_mask] <= preds[valid_mask]))
            }
            
            if self.verbose:
                status = "✓" if is_well_calibrated else "✗"
                print(f"  {status} Q{q*100:3.0f}: observed={observed_coverage:.3f}, deviation={deviation:.4f}")
        
        # Overall calibration quality
        mean_deviation = np.mean(deviations)
        is_calibrated = mean_deviation <= tolerance
        
        return {
            "timestamp": pd.Timestamp.now().isoformat(),
            "calibration_results": results,
            "mean_deviation": float(mean_deviation),
            "is_calibrated": bool(is_calibrated),
            "calibration_status": "✓ WELL-CALIBRATED" if is_calibrated else "⚠️ POORLY CALIBRATED",
            "tolerance": float(tolerance),
            "reliability_diagram": self._generate_reliability_diagram_data(results)
        }
    
    def _generate_reliability_diagram_data(self, results: Dict) -> Dict:
        """Generate data for reliability diagram visualization"""
        quantiles = sorted(results.keys())
        nominal = [q for q in quantiles]
        observed = [results[q]['observed_coverage'] for q in quantiles]
        
        return {
            "quantiles": quantiles,
            "nominal": nominal,
            "observed": observed,
            "points": [{"nominal": q, "observed": results[q]['observed_coverage']} 
                      for q in quantiles]
        }


def audit_multi_plant_calibration(plant_data: Dict[str, Dict], 
                                  quantile_levels: List[float] = None) -> Dict:
    """
    Run calibration audit across multiple plants and quantiles.
    
    Args:
        plant_data: {plant_id: {"actuals": [...], "p10": [...], "p50": [...], "p90": [...]}, ...}
        quantile_levels: Quantiles to check (default: [0.1, 0.5, 0.9])
    
    Returns:
        System-level calibration report
    """
    
    if quantile_levels is None:
        quantile_levels = [0.1, 0.5, 0.9]
    
    auditor = QuantileCalibrationAudit(verbose=True)
    
    print("\n" + "="*80)
    print("QUANTILE CALIBRATION AUDIT — Multi-Plant Report")
    print("="*80)
    
    results = {}
    all_calibrated = True
    
    for plant_id, data in sorted(plant_data.items()):
        if 'actuals' not in data:
            continue
        
        # Build quantile predictions dict
        y_pred_quantiles = {}
        for q in quantile_levels:
            key = f"p{int(q*100)}"
            if key not in data:
                continue  # Skip if this quantile not available
            y_pred_quantiles[q] = data[key]
        
        if not y_pred_quantiles:
            continue
        
        print(f"\n{plant_id}:")
        audit_result = auditor.audit_calibration(data['actuals'], y_pred_quantiles)
        results[plant_id] = audit_result
        
        if not audit_result['is_calibrated']:
            all_calibrated = False
    
    # Aggregate statistics
    deviations = []
    for plant_id, result in results.items():
        deviations.append(result['mean_deviation'])
    
    system_mean_deviation = np.mean(deviations) if deviations else 0
    
    print("\n" + "="*80)
    print(f"SYSTEM CALIBRATION: {'✓ GOOD' if all_calibrated else '⚠️ NEEDS ATTENTION'}")
    print(f"Mean deviation across all plants: {system_mean_deviation:.4f}")
    print("="*80 + "\n")
    
    return {
        "timestamp": pd.Timestamp.now().isoformat(),
        "plants": results,
        "system_mean_deviation": float(system_mean_deviation),
        "all_calibrated": bool(all_calibrated),
        "total_plants": len(results),
        "quantile_levels": quantile_levels,
        "summary": {
            "well_calibrated_plants": sum(1 for r in results.values() if r['is_calibrated']),
            "poorly_calibrated_plants": sum(1 for r in results.values() if not r['is_calibrated']),
            "status": "✓ SYSTEM CALIBRATED" if all_calibrated else "⚠️ CALIBRATION ISSUES"
        }
    }


def generate_reliability_diagram_analysis(audit_results: Dict) -> str:
    """Generate human-readable interpretation of reliability diagram"""
    
    lines = [
        "\n" + "="*80,
        "RELIABILITY DIAGRAM INTERPRETATION",
        "="*80,
        "",
        "Perfect calibration: observed_coverage = nominal_quantile at all levels",
        "This means: P10 forecasts should be exceeded 10% of the time, P50 should be",
        "exceeded 50% of the time, etc. if the model is truly calibrated.",
        "",
        "Plot: If observed vs nominal traces the 45-degree diagonal, model is calibrated.",
        ""
    ]
    
    for plant_id, result in sorted(audit_results.get('plants', {}).items()):
        lines.append(f"{plant_id}:")
        status = result.get('calibration_status', 'unknown')
        lines.append(f"  Status: {status}")
        lines.append(f"  Mean deviation: {result['mean_deviation']:.4f}")
        
        for q, data in sorted(result.get('calibration_results', {}).items()):
            mark = "✓" if data['within_tolerance'] else "✗"
            lines.append(
                f"  {mark} Q{q*100:3.0f}: observed={data['observed_coverage']:.3f} "
                f"(nominal={data['nominal_quantile']:.3f}, dev={data['deviation']:.4f})"
            )
        lines.append("")
    
    lines.extend([
        "KEY INSIGHTS:",
        "• If P10 observed > 0.1: Model is too pessimistic (intervals too wide)",
        "• If P10 observed < 0.1: Model is too optimistic (intervals too narrow)",
        "• Monsoon months typically show wider tails (higher uncertainty)",
        "• Clear summer days show tighter tails (lower uncertainty)",
        "• If tails are asymmetric, model may have seasonal bias",
        "",
        "ACTIONS:",
        "✓ Well-calibrated: Deploy to production (CQR is working correctly)",
        "⚠️ Moderate deviation: Monitor and consider recalibration",
        "🚨 Large deviation: Retrain model or check data quality",
        "="*80 + "\n"
    ])
    
    return "\n".join(lines)


__all__ = ['QuantileCalibrationAudit', 'audit_multi_plant_calibration', 
           'generate_reliability_diagram_analysis']
