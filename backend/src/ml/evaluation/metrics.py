"""
Person 4 — Evaluation Harness (Day 1)
======================================
This file owns ALL metric computation for the project.
It is intentionally built BEFORE any real model exists —
so the moment Person 2 ships forecasts, we can plug them in
and get numbers immediately.

What this file does:
  - Defines the temporal train/val/test split (no shuffling, ever)
  - Implements nMAE, nRMSE, CRPS, and coverage
  - Wraps everything in a single evaluate() function
  - Returns results broken down by: plant, hour-of-day, and season

What this file does NOT do (yet — those are Day 2+):
  - Implement baselines (persistence, climatological, NWP regression)
  - Run stress tests on edge-case scenarios
  - Generate comparison tables or plots

Inputs expected (Day 2 onwards, from Person 2):
  A DataFrame with columns:
    timestamp   : datetime
    plant_id    : str
    actual      : float  (MW)
    p50         : float  (point forecast, MW)
    p10         : float  (lower bound, MW)
    p90         : float  (upper bound, MW)

Inputs expected from Person 1:
  The raw synthetic dataset CSV so we can do the temporal split here.
  Path: data/synthetic_features.csv  (Person 1 will confirm exact name)
"""

import numpy as np
import pandas as pd
from typing import Optional


# ──────────────────────────────────────────────────────────────
# 1.  TEMPORAL SPLIT
#     Rule: NEVER shuffle. The test set is the LAST 2 months,
#     validation is the 2 months before that, everything else
#     is training. This prevents data leakage.
# ──────────────────────────────────────────────────────────────

def temporal_split(df: pd.DataFrame, timestamp_col: str = "timestamp"):
    """
    Splits a time-series DataFrame into train / validation / test.

    Split boundaries (all chronological, no shuffling):
      - Test  : last 2 months
      - Val   : 2 months before test
      - Train : everything before val

    Parameters
    ----------
    df : pd.DataFrame
        Full dataset with a datetime column.
    timestamp_col : str
        Name of the datetime column.

    Returns
    -------
    train_df, val_df, test_df : pd.DataFrame
    """
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    df = df.sort_values(timestamp_col).reset_index(drop=True)

    end_date   = df[timestamp_col].max()
    test_start = end_date - pd.DateOffset(months=2)
    val_start  = test_start - pd.DateOffset(months=2)

    train_df = df[df[timestamp_col] <  val_start].reset_index(drop=True)
    val_df   = df[(df[timestamp_col] >= val_start) &
                  (df[timestamp_col] <  test_start)].reset_index(drop=True)
    test_df  = df[df[timestamp_col] >= test_start].reset_index(drop=True)

    print(f"[Temporal Split]")
    print(f"  Train : {train_df[timestamp_col].min().date()} -> {train_df[timestamp_col].max().date()}  ({len(train_df):,} rows)")
    print(f"  Val   : {val_df[timestamp_col].min().date()}   -> {val_df[timestamp_col].max().date()}    ({len(val_df):,} rows)")
    print(f"  Test  : {test_df[timestamp_col].min().date()}  -> {test_df[timestamp_col].max().date()}   ({len(test_df):,} rows)")

    return train_df, val_df, test_df


# ──────────────────────────────────────────────────────────────
# 2.  CORE METRICS
# ──────────────────────────────────────────────────────────────

def nmae(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    Normalized Mean Absolute Error.
    MAE divided by the mean of actuals.
    Lets us compare accuracy across plants of different capacities.

    Lower is better. 0.10 = 10% average error relative to mean output.
    """
    actual    = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    mean_actual = np.mean(actual)
    if mean_actual == 0:
        return np.nan  # avoid div-by-zero for nighttime-only windows

    return float(np.mean(np.abs(actual - predicted)) / mean_actual)


def nrmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    Normalized Root Mean Squared Error.
    RMSE divided by mean of actuals.
    Penalizes large errors more than nMAE — useful for flagging outlier misses.

    Lower is better.
    """
    actual    = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    mean_actual = np.mean(actual)
    if mean_actual == 0:
        return np.nan

    return float(np.sqrt(np.mean((actual - predicted) ** 2)) / mean_actual)


def crps_gaussian(actual: np.ndarray,
                  p50: np.ndarray,
                  p10: np.ndarray,
                  p90: np.ndarray) -> float:
    """
    Continuous Ranked Probability Score (CRPS) — Gaussian approximation.

    CRPS jointly rewards accurate point forecasts AND well-calibrated
    uncertainty intervals. A model that says "I'm very confident" but
    is wrong gets penalized harder than one that admits uncertainty.

    Lower is better. CRPS = 0 means perfect forecast.

    How it works:
      We treat the P10/P90 interval as a Gaussian distribution:
        mean  = P50
        sigma = (P90 - P10) / (2 * 1.28)   [1.28 = z-score for 80% interval]

      Then compute the closed-form CRPS for a Gaussian:
        CRPS = sigma * (z*(2*Phi(z)-1) + 2*phi(z) - 1/sqrt(pi))
      where z = (actual - mean) / sigma

    Reference: Gneiting & Raftery (2007), "Strictly Proper Scoring Rules"
    """
    from scipy.stats import norm

    actual = np.asarray(actual, dtype=float)
    mu     = np.asarray(p50,    dtype=float)
    p10_a  = np.asarray(p10,    dtype=float)
    p90_a  = np.asarray(p90,    dtype=float)

    # Derive sigma from the 80% prediction interval
    sigma = (p90_a - p10_a) / (2 * 1.2816)  # 1.2816 = norm.ppf(0.9)
    sigma = np.maximum(sigma, 1e-6)          # guard against zero-width intervals

    z = (actual - mu) / sigma

    # Closed-form Gaussian CRPS
    crps_values = sigma * (
        z * (2 * norm.cdf(z) - 1)
        + 2 * norm.pdf(z)
        - 1 / np.sqrt(np.pi)
    )

    return float(np.mean(crps_values))


def prediction_interval_coverage(actual: np.ndarray,
                                  p10: np.ndarray,
                                  p90: np.ndarray) -> float:
    """
    Fraction of actual values that fall inside the [P10, P90] interval.

    Target: ~0.80 (80%) for an 80% prediction interval.
    If coverage << 0.80  -> intervals are too narrow (model is overconfident).
    If coverage >> 0.80  -> intervals are too wide  (model is underconfident).

    This is the calibration check. Person 2's CQR output should hit ~0.80.
    """
    actual = np.asarray(actual, dtype=float)
    p10    = np.asarray(p10,    dtype=float)
    p90    = np.asarray(p90,    dtype=float)

    inside = (actual >= p10) & (actual <= p90)
    return float(np.mean(inside))


# ──────────────────────────────────────────────────────────────
# 3.  SEASON HELPER
# ──────────────────────────────────────────────────────────────

def assign_season(month: int) -> str:
    """
    Karnataka season classification:
      Summer        : March-May    (3, 4, 5)
      Monsoon       : June-Sep     (6, 7, 8, 9)
      Post-Monsoon  : Oct-Nov      (10, 11)
      Winter        : Dec-Feb      (12, 1, 2)
    """
    if month in (3, 4, 5):
        return "Summer"
    elif month in (6, 7, 8, 9):
        return "Monsoon"
    elif month in (10, 11):
        return "Post-Monsoon"
    else:
        return "Winter"


# ──────────────────────────────────────────────────────────────
# 4.  MASTER EVALUATE FUNCTION
#     This is the single callable the rest of the codebase uses.
# ──────────────────────────────────────────────────────────────

def evaluate(
    forecast_df: pd.DataFrame,
    plant_type_map: Optional[dict] = None,
    timestamp_col: str = "timestamp",
) -> dict:
    """
    Master evaluation function. Takes a forecast DataFrame and returns
    all metrics broken down by overall, per-plant, per-hour, and per-season.

    Parameters
    ----------
    forecast_df : pd.DataFrame
        Must contain columns:
          timestamp, plant_id, actual, p50, p10, p90
    plant_type_map : dict, optional
        Maps plant_id -> "solar" or "wind".
        e.g. {"PVG_S1": "solar", "GDG_W1": "wind", ...}
        If None, all plants are treated as "unknown".
    timestamp_col : str
        Name of the datetime column.

    Returns
    -------
    dict with keys:
      overall        : aggregate metrics across all plants & hours
      by_plant       : per-plant metrics dict
      by_hour        : metrics per hour-of-day (0-23)
      by_season      : metrics per Karnataka season
      solar_summary  : aggregate for solar plants only
      wind_summary   : aggregate for wind plants only
    """
    df = forecast_df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col])

    # Add helper columns
    df["hour"]        = df[timestamp_col].dt.hour
    df["month"]       = df[timestamp_col].dt.month
    df["season"]      = df["month"].apply(assign_season)

    if plant_type_map:
        df["plant_type"] = df["plant_id"].map(plant_type_map).fillna("unknown")
    else:
        df["plant_type"] = "unknown"

    def _metrics(sub: pd.DataFrame) -> dict:
        """Compute all metrics on a sub-DataFrame."""
        if len(sub) == 0:
            return {}
        a   = sub["actual"].values
        p50 = sub["p50"].values
        p10 = sub["p10"].values
        p90 = sub["p90"].values

        result = {
            "n_samples"   : int(len(sub)),
            "nmae"        : round(nmae(a, p50),    4),
            "nrmse"       : round(nrmse(a, p50),   4),
            "coverage_80" : round(prediction_interval_coverage(a, p10, p90), 4),
        }

        # CRPS needs scipy — graceful fallback if not installed
        try:
            result["crps"] = round(crps_gaussian(a, p50, p10, p90), 4)
        except ImportError:
            result["crps"] = None

        return result

    # ── Overall ──────────────────────────────────────────────
    overall = _metrics(df)

    # ── Per plant ────────────────────────────────────────────
    by_plant = {}
    for plant_id, grp in df.groupby("plant_id"):
        by_plant[plant_id] = _metrics(grp)

    # ── Per hour of day ──────────────────────────────────────
    by_hour = {}
    for hour, grp in df.groupby("hour"):
        by_hour[int(hour)] = _metrics(grp)

    # ── Per season ───────────────────────────────────────────
    by_season = {}
    for season, grp in df.groupby("season"):
        by_season[season] = _metrics(grp)

    # ── Solar vs Wind summary ────────────────────────────────
    solar_df = df[df["plant_type"] == "solar"]
    wind_df  = df[df["plant_type"] == "wind"]

    solar_summary = _metrics(solar_df) if len(solar_df) > 0 else {}
    wind_summary  = _metrics(wind_df)  if len(wind_df)  > 0 else {}

    return {
        "overall"      : overall,
        "by_plant"     : by_plant,
        "by_hour"      : by_hour,
        "by_season"    : by_season,
        "solar_summary": solar_summary,
        "wind_summary" : wind_summary,
    }


# ──────────────────────────────────────────────────────────────
# 5.  get_results() — the hook evaluationService.py calls
#     Right now returns mock data shaped like real output.
#     On Day 3, replace mock with a real call to evaluate().
# ──────────────────────────────────────────────────────────────

def get_results() -> dict:
    """
    Called by evaluationService.py.
    Returns evaluation results in the shape the API / dashboard expects.

    TODO (Day 3): Replace mock below with:
        forecast_df = load_test_forecasts()   # Person 2's output
        return evaluate(forecast_df, plant_type_map=PLANT_TYPE_MAP)
    """
    return {
        "baselines": {
            "persistence":    {"nmae_solar": 0.21, "nmae_wind": 0.24, "crps": 0.33},
            "climatological": {"nmae_solar": 0.17, "nmae_wind": 0.20, "crps": 0.29},
            "raw_nwp":        {"nmae_solar": 0.15, "nmae_wind": 0.18, "crps": 0.26},
        },
        "model": {
            "nmae_solar": None,  # filled Day 3 when Person 2's model is ready
            "nmae_wind":  None,
            "crps":       None,
        },
        "improvement_over_persistence": {
            "nmae_solar_pct": None,
            "nmae_wind_pct":  None,
            "crps_pct":       None,
        },
    }