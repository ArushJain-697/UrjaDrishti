"""
PERSON 3 — Explainability & Reconciliation
Day 1: Reconciliation skeleton
- Basic hierarchical structure
- MinT implementation placeholder for Day 3
"""

import numpy as np
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# MOCK RECONCILIATION FOR DAY 1
# ============================================================

def get_reconciled(plant_forecasts: Dict[str, List[float]] = None,
                   cluster_forecast: List[float] = None,
                   cluster_name: str = "cluster_a") -> Dict:
    """
    Hierarchical reconciliation using MinTrace (placeholder for Day 3)
    
    Args:
        plant_forecasts: Dict of {plant_id: [p50 values for 24 hours]}
        cluster_forecast: Cluster-level forecast [p50 values for 24 hours]
        cluster_name: Name of cluster
    
    Returns:
        {
            "cluster_name": {
                "pre_mint": {"plant_sum": float, "cluster_forecast": float, "consistent": bool},
                "post_mint": {"plant_sum": float, "cluster_forecast": float, "consistent": bool},
                "reconciled_forecasts": {plant_id: [values]}
            }
        }
    """
    try:
        # Day 1 mock data: 6 plants across 2 clusters
        if plant_forecasts is None:
            plant_forecasts = {
                f"plant_{i}": np.random.uniform(100, 800, 24).tolist()
                for i in range(1, 7)
            }
        
        if cluster_forecast is None:
            cluster_forecast = (
                np.mean([np.array(v) for v in plant_forecasts.values()], axis=0) * 6
            ).tolist()
        
        # Pre-reconciliation consistency check
        plant_sum_pre = sum(sum(v) for v in plant_forecasts.values())
        cluster_sum_pre = sum(cluster_forecast)
        consistent_pre = abs(plant_sum_pre - cluster_sum_pre) < 100  # Within 100 units
        
        # Day 3 TODO: Implement actual MinT reconciliation
        # For now, just scale plants proportionally to match cluster
        scale_factor = cluster_sum_pre / plant_sum_pre if plant_sum_pre > 0 else 1.0
        reconciled_forecasts = {
            plant_id: [v * scale_factor for v in values]
            for plant_id, values in plant_forecasts.items()
        }
        
        # Post-reconciliation consistency check
        plant_sum_post = sum(sum(v) for v in reconciled_forecasts.values())
        cluster_sum_post = sum(cluster_forecast)
        consistent_post = abs(plant_sum_post - cluster_sum_post) < 10  # Tighter tolerance
        
        return {
            cluster_name: {
                "pre_mint": {
                    "plant_sum": round(plant_sum_pre, 2),
                    "cluster_forecast": round(cluster_sum_pre, 2),
                    "consistent": consistent_pre,
                    "error_pct": round(abs(plant_sum_pre - cluster_sum_pre) / cluster_sum_pre * 100, 2)
                },
                "post_mint": {
                    "plant_sum": round(plant_sum_post, 2),
                    "cluster_forecast": round(cluster_sum_post, 2),
                    "consistent": consistent_post,
                    "error_pct": round(abs(plant_sum_post - cluster_sum_post) / cluster_sum_post * 100, 2)
                },
                "reconciled_forecasts": {
                    k: [round(v, 2) for v in vals]
                    for k, vals in reconciled_forecasts.items()
                }
            }
        }
    
    except Exception as e:
        print(f"[ERROR] Reconciliation failed: {e}")
        return {
            cluster_name: {
                "error": str(e),
                "status": "reconciliation_unavailable"
            }
        }


__all__ = ['get_reconciled']