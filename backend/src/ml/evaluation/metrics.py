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

import os
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd


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


def _quantile_ensemble_from_p10_p50_p90(
    p10: np.ndarray,
    p50: np.ndarray,
    p90: np.ndarray,
    n_members: int = 41,
) -> np.ndarray:
    """
    Build an ensemble matrix from available quantiles using piecewise linear
    interpolation of the empirical quantile function.
    """
    if n_members < 3:
        raise ValueError("n_members must be >= 3")

    q_levels = np.array([0.1, 0.5, 0.9], dtype=float)
    target_q = np.linspace(0.01, 0.99, n_members)

    p10_arr = np.asarray(p10, dtype=float)
    p50_arr = np.asarray(p50, dtype=float)
    p90_arr = np.asarray(p90, dtype=float)

    members = np.empty((len(p10_arr), n_members), dtype=float)
    for idx in range(len(p10_arr)):
        values = np.array([p10_arr[idx], p50_arr[idx], p90_arr[idx]], dtype=float)
        values = np.maximum.accumulate(values)  # enforce non-decreasing quantiles
        members[idx, :] = np.interp(target_q, q_levels, values)
    return members


def crps_ensemble_score(
    actual: np.ndarray,
    p50: np.ndarray,
    p10: np.ndarray,
    p90: np.ndarray,
    fallback_to_gaussian: bool = True,
) -> float:
    """
    CRPS computed with properscoring.crps_ensemble from quantile-derived members.
    """
    try:
        import properscoring as ps
    except ImportError:
        if fallback_to_gaussian:
            return crps_gaussian(actual, p50, p10, p90)
        raise

    actual_arr = np.asarray(actual, dtype=float)
    members = _quantile_ensemble_from_p10_p50_p90(p10, p50, p90)
    crps_vals = ps.crps_ensemble(actual_arr, members)
    return float(np.mean(crps_vals))


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


def sharpness_score(p10: np.ndarray, p90: np.ndarray, capacity_mw: np.ndarray) -> float:
    """
    Mean interval width normalized by capacity.
    """
    p10_arr = np.asarray(p10, dtype=float)
    p90_arr = np.asarray(p90, dtype=float)
    cap_arr = np.asarray(capacity_mw, dtype=float)
    valid = cap_arr > 0
    if not np.any(valid):
        return np.nan
    width = p90_arr[valid] - p10_arr[valid]
    return float(np.mean(width / cap_arr[valid]))


def quantile_calibration_audit(
    y_true: np.ndarray,
    y_pred_quantiles: Sequence[np.ndarray],
    quantile_levels: Sequence[float],
) -> dict:
    """
    Reliability-style calibration audit over one or more quantile levels.
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    if len(y_pred_quantiles) != len(quantile_levels):
        raise ValueError("y_pred_quantiles and quantile_levels lengths must match")

    rows = []
    for level, pred in zip(quantile_levels, y_pred_quantiles):
        pred_arr = np.asarray(pred, dtype=float)
        observed = float(np.mean(y_true_arr <= pred_arr))
        rows.append(
            {
                "quantile": float(level),
                "observed": observed,
                "abs_error": float(abs(observed - float(level))),
            }
        )

    max_abs_error = max(row["abs_error"] for row in rows) if rows else np.nan
    mean_abs_error = float(np.mean([row["abs_error"] for row in rows])) if rows else np.nan
    return {
        "points": rows,
        "mean_abs_calibration_error": mean_abs_error,
        "max_abs_calibration_error": float(max_abs_error),
    }


def plot_quantile_reliability(audit: dict, save_path: str) -> None:
    """
    Save a reliability diagram (observed vs nominal quantiles).
    """
    import matplotlib.pyplot as plt

    points = audit.get("points", [])
    if not points:
        raise ValueError("Audit has no points to plot")

    x = [row["quantile"] for row in points]
    y = [row["observed"] for row in points]

    plt.figure(figsize=(6, 6))
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect calibration")
    plt.plot(x, y, marker="o", linewidth=2, label="Model")
    plt.xlabel("Nominal quantile")
    plt.ylabel("Observed fraction below quantile")
    plt.title("Quantile Reliability Diagram")
    plt.legend()
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


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
    include_coverage_90: bool = False,
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

        if include_coverage_90 and {"p05", "p95"}.issubset(sub.columns):
            result["coverage_90"] = round(
                prediction_interval_coverage(a, sub["p05"].values, sub["p95"].values),
                4,
            )

        if "capacity_mw" in sub.columns:
            sharp = sharpness_score(p10, p90, sub["capacity_mw"].values)
            result["sharpness"] = round(sharp, 4) if not np.isnan(sharp) else None

        # CRPS via properscoring, with Gaussian fallback
        try:
            result["crps"] = round(crps_ensemble_score(a, p50, p10, p90), 4)
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

    calibration = quantile_calibration_audit(
        df["actual"].values,
        [df["p10"].values, df["p50"].values, df["p90"].values],
        [0.10, 0.50, 0.90],
    )

    return {
        "overall"      : overall,
        "by_plant"     : by_plant,
        "by_hour"      : by_hour,
        "by_season"    : by_season,
        "solar_summary": solar_summary,
        "wind_summary" : wind_summary,
        "quantile_calibration": calibration,
    }


# ──────────────────────────────────────────────────────────────
# 5.  get_results() — the hook evaluationService.py calls
#     Right now returns mock data shaped like real output.
#     On Day 3, replace mock with a real call to evaluate().
# ──────────────────────────────────────────────────────────────

def resolve_evaluation_data_paths(feature_path: Optional[str] = None,
                                  raw_weather_path: Optional[str] = None) -> dict:
    """
    Resolve default evaluation CSV paths relative to repository root.
    """
    repo_root = Path(__file__).resolve().parents[4]
    data_dir = repo_root / "data"
    return {
        "feature_matrix": str(Path(feature_path) if feature_path else data_dir / "feature_matrix_final.csv"),
        "raw_weather": str(Path(raw_weather_path) if raw_weather_path else data_dir / "raw_weather_data.csv"),
    }


def _build_model_test_forecast(feature_path: str) -> Optional[pd.DataFrame]:
    """
    Build model predictions on temporal test split for evaluation.
    """
    import joblib
    from src.ml.forecasting.feature_engineering import transform
    from src.ml.forecasting.model import predict_stage1
    from src.ml.forecasting.predict import _STAGE1_PATH

    if not os.path.exists(_STAGE1_PATH):
        print(f"[get_results] Stage-1 model missing at {_STAGE1_PATH}; model metrics set to None")
        return None

    df = pd.read_csv(feature_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    _, _, test_df = temporal_split(df, timestamp_col="timestamp")

    stage1_model = joblib.load(_STAGE1_PATH)
    X_test, _ = transform(test_df)
    p50, p10, p90 = predict_stage1(stage1_model, X_test, return_pis=True)

    out = test_df[["timestamp", "plant_id", "actual_generation_mw"]].copy()
    out = out.rename(columns={"actual_generation_mw": "actual"})
    out["p50"] = p50
    out["p10"] = p10
    out["p90"] = p90
    if "capacity_mw" in test_df.columns:
        out["capacity_mw"] = test_df["capacity_mw"].values
    return out


def get_results() -> dict:
    """
    Called by evaluationService.py.
    Returns evaluation results in the shape the API / dashboard expects.

    Priority:
      1. _eval_cache.json  — pre-computed locally, committed to the repo.
                             This is what runs on Railway (no data CSV available).
      2. Live computation  — runs if the feature CSV is present (local dev).
      3. Static mock       — last resort if both above fail.
    """
    import json

    _HERE = Path(__file__).resolve().parent
    CACHE_FILE = _HERE / "_eval_cache.json"

    # ── 1. Try pre-computed cache ────────────────────────────────────────
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                cached = json.load(f)
            print("[get_results] Loaded evaluation results from cache.")
            return cached
        except Exception as e:
            print(f"[get_results] Cache load failed: {e} — falling back to live computation")

    # ── 2. Try live computation (needs data CSV) ─────────────────────────
    from src.ml.evaluation.baselines import run_all_baselines
    from src.ml.evaluation.baselines import PLANT_TYPE_MAP

    paths = resolve_evaluation_data_paths()
    feature_path = paths["feature_matrix"]
    raw_weather_path = paths["raw_weather"]
    baseline_results = None

    if os.path.exists(feature_path):
        try:
            baseline_results = run_all_baselines(feature_path, raw_weather_path)
        except Exception as e:
            print(f"[get_results] Baseline run failed: {e} — using mock")

    def _fmt(b):
        """Extract solar/wind nMAE and CRPS from a baseline result dict."""
        if b is None:
            return {
                "nmae_solar": None, "nmae_wind": None,
                "nrmse_solar": None, "nrmse_wind": None,
                "coverage_80": None, "coverage_90": None,
                "sharpness": None, "crps": None
            }
        return {
            "nmae_solar": b.get("solar_summary", {}).get("nmae"),
            "nmae_wind" : b.get("wind_summary",  {}).get("nmae"),
            "nrmse_solar": b.get("solar_summary", {}).get("nrmse"),
            "nrmse_wind" : b.get("wind_summary",  {}).get("nrmse"),
            "coverage_80": b.get("overall", {}).get("coverage_80"),
            "coverage_90": b.get("overall", {}).get("coverage_90"),
            "sharpness"  : b.get("overall", {}).get("sharpness"),
            "crps"      : b.get("overall",        {}).get("crps"),
        }

    if baseline_results:
        baselines = {
            "persistence"   : _fmt(baseline_results["persistence"]),
            "climatological": _fmt(baseline_results["climatological"]),
            "raw_nwp"       : _fmt(baseline_results["raw_nwp"]),
        }
    else:
        baselines = {
            "persistence":    {"nmae_solar": 0.21, "nmae_wind": 0.24, "nrmse_solar": 0.29, "nrmse_wind": 0.31, "coverage_80": 0.79, "coverage_90": None, "sharpness": 0.28, "crps": 0.33},
            "climatological": {"nmae_solar": 0.17, "nmae_wind": 0.20, "nrmse_solar": 0.24, "nrmse_wind": 0.26, "coverage_80": 0.81, "coverage_90": None, "sharpness": 0.25, "crps": 0.29},
            "raw_nwp":        {"nmae_solar": 0.15, "nmae_wind": 0.18, "nrmse_solar": 0.21, "nrmse_wind": 0.23, "coverage_80": 0.82, "coverage_90": None, "sharpness": 0.23, "crps": 0.26},
        }

    model_evals = None
    model = {
        "nmae_solar": None, "nmae_wind": None,
        "nrmse_solar": None, "nrmse_wind": None,
        "coverage_80": None, "coverage_90": None,
        "sharpness": None, "crps": None,
    }
    if os.path.exists(feature_path):
        try:
            model_forecasts = _build_model_test_forecast(feature_path)
            if model_forecasts is not None:
                model_evals = evaluate(model_forecasts, plant_type_map=PLANT_TYPE_MAP, include_coverage_90=True)
                model = {
                    "nmae_solar": model_evals.get("solar_summary", {}).get("nmae"),
                    "nmae_wind": model_evals.get("wind_summary", {}).get("nmae"),
                    "nrmse_solar": model_evals.get("solar_summary", {}).get("nrmse"),
                    "nrmse_wind": model_evals.get("wind_summary", {}).get("nrmse"),
                    "coverage_80": model_evals.get("overall", {}).get("coverage_80"),
                    "coverage_90": model_evals.get("overall", {}).get("coverage_90"),
                    "sharpness": model_evals.get("overall", {}).get("sharpness"),
                    "crps": model_evals.get("overall", {}).get("crps"),
                }
        except Exception as e:
            print(f"[get_results] Model evaluation failed: {e} — model metrics set to None")

    def _improvement_pct(model_val, baseline_val):
        if model_val is None or baseline_val is None or baseline_val == 0:
            return None
        return round((baseline_val - model_val) / baseline_val * 100, 1)

    p = baselines["persistence"]
    improvement = {
        "nmae_solar_pct": _improvement_pct(model["nmae_solar"], p["nmae_solar"]),
        "nmae_wind_pct" : _improvement_pct(model["nmae_wind"],  p["nmae_wind"]),
        "crps_pct"      : _improvement_pct(model["crps"],       p["crps"]),
    }

    by_season = {}
    by_plant  = {}
    if model_evals:
        by_season = model_evals.get("by_season", {})
        by_plant  = model_evals.get("by_plant", {})

    return {
        "baselines"                 : baselines,
        "model"                     : model,
        "improvement_over_persistence": improvement,
        "model_evaluation"          : model_evals,
        "by_season"                 : by_season,
        "by_plant"                  : by_plant,
    }