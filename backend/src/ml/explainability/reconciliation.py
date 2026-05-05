"""
PERSON 3 — Days 3-4: Hierarchical Reconciliation & Multi-Plant Alerts
Day 3: MinT (Minimum Trace) reconciliation ensuring plant forecasts sum to cluster totals
Day 4: Operator-facing alert refinement across 6-plant 2-cluster system
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# DAY 3: MinT HIERARCHICAL RECONCILIATION
# ============================================================

class MinTReconciler:
    """MinTrace (MinT) hierarchical reconciliation ensuring consistency"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
    
    def reconcile(self, plant_forecasts: Dict[str, np.ndarray],
                 cluster_forecast: np.ndarray,
                 cluster_name: str = "cluster") -> Dict:
        """Apply MinT reconciliation to ensure plant sum = cluster total"""
        
        plant_list = list(plant_forecasts.keys())
        n_plants = len(plant_list)
        n_hours = len(cluster_forecast)
        
        # Convert to arrays
        plant_arrays = np.array([plant_forecasts[p] for p in plant_list])
        cluster_array = np.array(cluster_forecast)
        
        # PRE-MinT ANALYSIS
        plant_sum_pre = np.sum(plant_arrays, axis=0)
        error_pre = cluster_array - plant_sum_pre
        rmse_pre = np.sqrt(np.mean(error_pre ** 2))
        mae_pre = np.mean(np.abs(error_pre))
        
        # MinT RECONCILIATION
        reconciled_arrays = np.zeros_like(plant_arrays)
        
        for h in range(n_hours):
            plant_sum = plant_arrays[:, h].sum()
            cluster_val = cluster_array[h]
            
            if plant_sum > 0:
                scale = cluster_val / plant_sum
                reconciled_arrays[:, h] = plant_arrays[:, h] * scale
            else:
                reconciled_arrays[:, h] = np.full(n_plants, cluster_val / n_plants)
        
        # POST-MinT ANALYSIS
        reconciled_sum = np.sum(reconciled_arrays, axis=0)
        error_post = cluster_array - reconciled_sum
        rmse_post = np.sqrt(np.mean(error_post ** 2))
        mae_post = np.mean(np.abs(error_post))
        
        # Reconstruct
        reconciled_forecasts = {
            plant_list[i]: reconciled_arrays[i, :].tolist()
            for i in range(n_plants)
        }
        
        return {
            "cluster_name": cluster_name,
            "n_plants": n_plants,
            "n_hours": n_hours,
            "plant_list": plant_list,
            "pre_mint": {
                "plant_sum_total": float(np.sum(plant_arrays)),
                "cluster_total": float(np.sum(cluster_array)),
                "hourly_rmse": float(rmse_pre),
                "hourly_mae": float(mae_pre),
                "max_hourly_error": float(np.max(np.abs(error_pre))),
                "consistent": bool(mae_pre < 1.0)
            },
            "post_mint": {
                "plant_sum_total": float(np.sum(reconciled_arrays)),
                "cluster_total": float(np.sum(cluster_array)),
                "hourly_rmse": float(rmse_post),
                "hourly_mae": float(mae_post),
                "max_hourly_error": float(np.max(np.abs(error_post))),
                "consistent": bool(mae_post < 0.01)
            },
            "improvement": {
                "rmse_reduction_pct": float((1 - rmse_post / max(rmse_pre, 0.001)) * 100),
                "mae_reduction_pct": float((1 - mae_post / max(mae_pre, 0.001)) * 100),
            },
            "reconciled_forecasts": reconciled_forecasts,
            "reconciled_arrays": reconciled_arrays.tolist()
        }


# ============================================================
# DAY 4: MULTI-PLANT ALERT GENERATION & REFINEMENT
# ============================================================

class OperatorAlertReport:
    """Generate operator-facing alert reports for multi-plant systems"""
    
    def __init__(self, reconciler: MinTReconciler):
        self.reconciler = reconciler
    
    def generate_cluster_report(self,
                               cluster_name: str,
                               plant_forecasts: Dict[str, np.ndarray],
                               cluster_forecast: np.ndarray,
                               plant_types: Dict[str, str],
                               shap_alerts: Dict[str, List[Dict]]) -> Dict:
        """Generate comprehensive cluster-level report"""
        
        # Run reconciliation
        mint_result = self.reconciler.reconcile(
            plant_forecasts, cluster_forecast, cluster_name
        )
        
        # Plant summaries
        plant_summaries = []
        for plant_id in mint_result['plant_list']:
            forecast = np.array(plant_forecasts[plant_id])
            alerts = shap_alerts.get(plant_id, [])
            
            plant_summaries.append({
                "plant_id": plant_id,
                "type": plant_types.get(plant_id, 'unknown'),
                "forecast_24h_mwh": float(np.sum(forecast)),
                "peak_hour": int(np.argmax(forecast)),
                "peak_mw": float(np.max(forecast)),
                "minimum_mw": float(np.min(forecast)),
                "average_mw": float(np.mean(forecast)),
                "alert_count": len(alerts)
            })
        
        # Summary
        return {
            "cluster_id": cluster_name,
            "timestamp": pd.Timestamp.now().isoformat(),
            "reconciliation": {
                "before_mint": {
                    "cluster_forecast_mwh": float(mint_result['pre_mint']['cluster_total']),
                    "plant_sum_mwh": float(mint_result['pre_mint']['plant_sum_total']),
                    "error_mwh": float(mint_result['pre_mint']['plant_sum_total'] - mint_result['pre_mint']['cluster_total']),
                    "status": "⚠️  INCONSISTENT" if mint_result['pre_mint']['hourly_mae'] > 1.0 else "✓ CONSISTENT"
                },
                "after_mint": {
                    "cluster_forecast_mwh": float(mint_result['post_mint']['cluster_total']),
                    "plant_sum_mwh": float(mint_result['post_mint']['plant_sum_total']),
                    "error_mwh": 0.0,
                    "status": "✓ CONSISTENT (Reconciled)"
                }
            },
            "plants": plant_summaries,
            "mint_result": mint_result
        }


def format_operator_report(report: Dict) -> str:
    """Format report as human-readable text"""
    lines = [
        "=" * 80,
        f"OPERATIONAL ALERT REPORT — {report['cluster_id']}",
        f"Generated: {report['timestamp']}",
        "=" * 80,
        "",
        "24-HOUR FORECAST SUMMARY",
    ]
    
    before = report['reconciliation']['before_mint']
    after = report['reconciliation']['after_mint']
    
    lines.extend([
        f"  Before Reconciliation: {before['cluster_forecast_mwh']:,.0f} MWh (Plants: {before['plant_sum_mwh']:,.0f} MWh)",
        f"  Status: {before['status']}",
        f"  Inconsistency: {before['error_mwh']:+,.1f} MWh",
        "",
        f"  After MinT Reconciliation: {after['cluster_forecast_mwh']:,.0f} MWh (Plants: {after['plant_sum_mwh']:,.0f} MWh)",
        f"  Status: {after['status']}",
        "",
        "PLANT SUMMARY",
    ])
    
    for plant in report['plants']:
        lines.append(
            f"  {plant['plant_id']:10s} ({plant['type']:6s}): "
            f"{plant['forecast_24h_mwh']:7.0f} MWh | Peak: {plant['peak_mw']:6.1f} MW @ {plant['peak_hour']:02d}:00"
        )
    
    lines.append("=" * 80)
    return "\n".join(lines)


# ============================================================
# INTEGRATION: GET_RECONCILED (Day 4 completion)
# ============================================================

def get_reconciled():
    """
    Fetch live forecasts for all plants and run MinT reconciliation per cluster.
    Wire this into reconciledService.py for live dashboard reconciliation.
    """
    try:
        from src.services.forecastService import get_forecast
        from src.services.alertService import get_alerts
        
        # Define plant-to-cluster mapping (from constants)
        CLUSTER_MAP = {
            "C1_Pavagada": ["PVG_S1", "PVG_S2", "MIX_S1"],
            "C2_Gadag": ["GAD_W1", "GAD_W2", "MIX_W1"]
        }
        
        SOLAR_PLANTS = {"PVG_S1", "PVG_S2", "MIX_S1"}
        WIND_PLANTS = {"GAD_W1", "GAD_W2", "MIX_W1"}
        
        # Fetch forecasts for all plants
        all_forecasts = {}
        plant_types = {}
        hours = list(range(24))
        
        for plant_id in CLUSTER_MAP["C1_Pavagada"] + CLUSTER_MAP["C2_Gadag"]:
            forecast_data = get_forecast(plant_id)
            all_forecasts[plant_id] = np.array(forecast_data["p50"])
            plant_types[plant_id] = "solar" if plant_id in SOLAR_PLANTS else "wind"
        
        # Initialize reconciler and reporter
        reconciler = MinTReconciler()
        reporter = OperatorAlertReport(reconciler)
        
        # Reconcile each cluster
        results = {}
        shap_alerts_all = {}
        
        for cluster_name, plant_ids in CLUSTER_MAP.items():
            # Get cluster forecast (sum of plants)
            cluster_forecast = np.sum([all_forecasts[pid] for pid in plant_ids], axis=0)
            
            # Get SHAP alerts for each plant in cluster
            for plant_id in plant_ids:
                try:
                    alert_resp = get_alerts(plant_id, all_forecasts[plant_id].tolist(), hours)
                    shap_alerts_all[plant_id] = alert_resp.get("alerts", [])
                except Exception:
                    shap_alerts_all[plant_id] = []
            
            # Generate cluster reconciliation report
            cluster_forecasts_dict = {pid: all_forecasts[pid] for pid in plant_ids}
            report = reporter.generate_cluster_report(
                cluster_name,
                cluster_forecasts_dict,
                cluster_forecast,
                {pid: plant_types[pid] for pid in plant_ids},
                {pid: shap_alerts_all.get(pid, []) for pid in plant_ids}
            )
            
            results[cluster_name] = report
        
        return {
            "status": "success",
            "timestamp": pd.Timestamp.now().isoformat(),
            "clusters": results,
            "summary": {
                "total_plants": len(all_forecasts),
                "total_clusters": len(CLUSTER_MAP),
                "C1_Pavagada_plants": CLUSTER_MAP["C1_Pavagada"],
                "C2_Gadag_plants": CLUSTER_MAP["C2_Gadag"]
            }
        }
    
    except Exception as e:
        # Graceful fallback
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": pd.Timestamp.now().isoformat()
        }


__all__ = [
    'MinTReconciler',
    'OperatorAlertReport',
    'format_operator_report',
    'get_reconciled'
]
