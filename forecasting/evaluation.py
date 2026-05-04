"""
evaluation.py — metrics for Stage-1 and Stage-2 comparison.
"""

import numpy as np


def nMAE(y_true, y_pred, capacity):
    """Fleet-normalised Mean Absolute Error."""
    return np.mean(np.abs(np.array(y_true) - np.array(y_pred))) / capacity


def nRMSE(y_true, y_pred, capacity):
    """Fleet-normalised Root Mean Squared Error."""
    return np.sqrt(np.mean((np.array(y_true) - np.array(y_pred)) ** 2)) / capacity


def CRPS_stub(y_true, p10, p90):
    """
    Placeholder for CRPS — returns P10–P90 interval coverage.
    Implement with MAPIE quantile outputs on Day 4.
    """
    y_true = np.array(y_true)
    return np.mean((y_true >= np.array(p10)) & (y_true <= np.array(p90)))


def evaluate(y_true, y_pred, plant_capacities):
    """Full fleet evaluation — returns nMAE and nRMSE."""
    y_true    = np.array(y_true)
    y_pred    = np.array(y_pred)
    total_cap = sum(plant_capacities.values()) if plant_capacities else 1.0

    return {
        'nMAE_fleet':  nMAE(y_true, y_pred, total_cap),
        'nRMSE_fleet': nRMSE(y_true, y_pred, total_cap),
    }


def compare_stages(y_true, s1_preds, s2_preds, plant_capacities):
    """
    Side-by-side comparison of Stage-1 vs Stage-2 corrected predictions.
    Used in intra-day evaluation (hours ≥ cutoff_hour only).
    """
    total_cap = sum(plant_capacities.values()) if plant_capacities else 1.0
    s1 = evaluate(y_true, s1_preds, plant_capacities)
    s2 = evaluate(y_true, s2_preds, plant_capacities)

    delta_nmae  = s1['nMAE_fleet']  - s2['nMAE_fleet']
    delta_nrmse = s1['nRMSE_fleet'] - s2['nRMSE_fleet']

    return {
        'stage1': s1,
        'stage2': s2,
        # Positive delta = Stage-2 is better
        'delta_nMAE':  delta_nmae,
        'delta_nRMSE': delta_nrmse,
        'pct_improvement_nMAE': delta_nmae / s1['nMAE_fleet'] * 100 if s1['nMAE_fleet'] else 0,
    }