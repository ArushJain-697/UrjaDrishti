"""
Person 4 — Baseline Implementations (Day 2)
=============================================
Three baselines that all of Person 2's model results get compared against.
These are implemented INDEPENDENTLY of Person 2's model — we own this file.

The three baselines:
  1. Persistence     — forecast = actual from exactly 24 hours ago
  2. Climatological  — forecast = historical mean for (plant, hour, month)
  3. Raw NWP LR      — per-plant linear regression on raw GHI/temp/wind_speed
                       (no physics transforms, no asset encoding)
                       This baseline specifically isolates the value of the
                       physics transforms and global model.

How Day 2 fits with the rest of the project
--------------------------------------------
- We ONLY need Person 1's synthetic dataset CSV to run baselines 1 and 2.
- Baseline 3 (Raw NWP LR) additionally needs the raw weather columns
  (ghi, temperature, wind_speed) in that same CSV.
- Person 2's model is NOT needed for any of this — baselines are independent.
- The results produced here feed directly into get_results() in metrics.py,
  which the API returns to the dashboard.

Expected CSV schema from Person 1
-----------------------------------
  timestamp    : datetime string
  plant_id     : str  (e.g. "PVG_S1", "GDG_W1")
  plant_type   : "solar" or "wind"
  actual_mw    : float  — actual generation in MW
  ghi          : float  — raw solar irradiance (W/m²)   [solar plants]
  temperature  : float  — ambient temperature (°C)      [solar plants]
  wind_speed   : float  — wind speed at hub height (m/s)[wind plants]

If the CSV has different column names, update COLUMN_MAP at the top of this file.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from typing import Optional

from src.ml.evaluation.metrics import (
    temporal_split,
    nmae,
    nrmse,
    crps_ensemble_score,
    prediction_interval_coverage,
    assign_season,
    resolve_evaluation_data_paths,
    sharpness_score,
)

# ── Column name mapping — matches feature_matrix_final.csv exactly ────────
# Key  = what our code uses internally
# Value = what Person 1's CSV actually has
COLUMN_MAP = {
    "timestamp"  : "timestamp",
    "plant_id"   : "plant_id",
    "plant_type" : "plant_type",
    "actual_mw"  : "actual_generation_mw",   # ← Person 1 uses this name
    "ghi"        : "GHI",                    # ← lives in raw_weather_data.csv
    "temperature": "temperature",
    "wind_speed" : "wind_speed",             # ← lives in raw_weather_data.csv
}

# ── Plant type map — matches asset_registry.csv and feature_matrix_final.csv
PLANT_TYPE_MAP = {
    "PVG_S1": "solar",
    "PVG_S2": "solar",
    "MIX_S1": "solar",
    "GAD_W1": "wind",   # ← real data uses GAD_, not GDG_
    "GAD_W2": "wind",
    "MIX_W1": "wind",
}

# ── File paths — relative to backend/ working directory ────────────────────
_DEFAULT_PATHS = resolve_evaluation_data_paths()
FEATURE_MATRIX_PATH  = _DEFAULT_PATHS["feature_matrix"]
RAW_WEATHER_PATH     = _DEFAULT_PATHS["raw_weather"]      # has GHI + wind_speed for NWP LR baseline


# ══════════════════════════════════════════════════════════════════════════════
# BASELINE 1 — PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════

def persistence_forecast(df: pd.DataFrame,
                         timestamp_col: str = "timestamp",
                         actual_col: str = "actual_mw",
                         plant_col: str = "plant_id") -> pd.DataFrame:
    """
    Day-ahead persistence baseline.

    For every row in the test set:
      forecast[t] = actual[t - 24h]

    This is the "dumbest" possible forecast — tomorrow looks exactly like today.
    It is surprisingly hard to beat and is the standard minimum bar.

    Parameters
    ----------
    df : pd.DataFrame
        Full dataset (all splits). Must be sorted by timestamp.
        Needs: timestamp, plant_id, actual_mw

    Returns
    -------
    pd.DataFrame with added column: persistence_forecast
    """
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    df = df.sort_values([plant_col, timestamp_col]).reset_index(drop=True)

    # Shift actual by 24 rows within each plant group (= 24 hours for hourly data)
    df["persistence_forecast"] = df.groupby(plant_col)[actual_col].shift(24)

    return df


# ══════════════════════════════════════════════════════════════════════════════
# BASELINE 2 — CLIMATOLOGICAL MEAN
# ══════════════════════════════════════════════════════════════════════════════

def climatological_forecast(train_df: pd.DataFrame,
                             test_df: pd.DataFrame,
                             timestamp_col: str = "timestamp",
                             actual_col: str = "actual_mw",
                             plant_col: str = "plant_id") -> pd.DataFrame:
    """
    Climatological mean baseline.

    For every (plant_id, hour_of_day, month) combination, compute the average
    actual generation from the TRAINING set. That average is the forecast for
    every matching row in the TEST set.

    This captures seasonal and diurnal patterns (solar peaks at noon, winter
    is dimmer than summer) but nothing about today's specific weather.

    Parameters
    ----------
    train_df : pd.DataFrame  — training set only (no leakage from test)
    test_df  : pd.DataFrame  — test set to generate forecasts for

    Returns
    -------
    test_df with added column: climatological_forecast
    """
    train = train_df.copy()
    test  = test_df.copy()

    for df in [train, test]:
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])

    train["hour"]  = train[timestamp_col].dt.hour
    train["month"] = train[timestamp_col].dt.month

    # Build lookup: mean generation per (plant, hour, month) from training data
    clim_table = (
        train.groupby([plant_col, "hour", "month"])[actual_col]
        .mean()
        .reset_index()
        .rename(columns={actual_col: "climatological_forecast"})
    )

    test["hour"]  = test[timestamp_col].dt.hour
    test["month"] = test[timestamp_col].dt.month

    test = test.merge(clim_table, on=[plant_col, "hour", "month"], how="left")

    # Fallback: if a (plant, hour, month) combo has no training history,
    # use the plant-level mean. This can happen at edges of the dataset.
    plant_mean = train.groupby(plant_col)[actual_col].mean().to_dict()
    mask = test["climatological_forecast"].isna()
    test.loc[mask, "climatological_forecast"] = (
        test.loc[mask, plant_col].map(plant_mean)
    )

    return test


# ══════════════════════════════════════════════════════════════════════════════
# BASELINE 3 — RAW NWP LINEAR REGRESSION (per plant, no physics transforms)
# ══════════════════════════════════════════════════════════════════════════════

def raw_nwp_lr_forecast(train_df: pd.DataFrame,
                         test_df: pd.DataFrame,
                         timestamp_col: str = "timestamp",
                         actual_col: str = "actual_mw",
                         plant_col: str = "plant_id",
                         plant_type_col: str = "plant_type") -> pd.DataFrame:
    """
    Raw NWP linear regression baseline — one LinearRegression model per plant.

    Features used:
      Solar plants : ghi, temperature, hour_of_day (raw integers — no sin/cos)
      Wind plants  : wind_speed, hour_of_day

    Deliberately uses:
      - RAW weather variables (no CMF, no power curve transform)
      - NO asset features (no capacity, no tilt, no lat/lon)
      - Separate model per plant (not global)

    This is the control condition. When Person 2's model beats this, it proves
    that the physics transforms + global architecture genuinely add value.

    Parameters
    ----------
    train_df, test_df : pd.DataFrame — pre-split datasets from temporal_split()

    Returns
    -------
    test_df with added column: raw_nwp_forecast
    """
    train = train_df.copy()
    test  = test_df.copy()

    for df in [train, test]:
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        df["hour"] = df[timestamp_col].dt.hour

    test["raw_nwp_forecast"] = np.nan
    models = {}

    for plant_id in train[plant_col].unique():
        tr = train[train[plant_col] == plant_id].copy()
        te = test[test[plant_col] == plant_id].copy()

        if len(tr) == 0 or len(te) == 0:
            continue

        # Determine plant type and feature set
        ptype = tr[plant_type_col].iloc[0] if plant_type_col in tr.columns else "unknown"

        if ptype == "solar":
            feature_cols = [c for c in ["ghi", "temperature", "hour"]
                            if c in tr.columns]
        elif ptype == "wind":
            feature_cols = [c for c in ["wind_speed", "hour"]
                            if c in tr.columns]
        else:
            # Fallback: use whatever numeric columns are available
            feature_cols = [c for c in ["ghi", "wind_speed", "temperature", "hour"]
                            if c in tr.columns]

        if len(feature_cols) == 0:
            # No weather features available — fall back to plant mean
            plant_mean = tr[actual_col].mean()
            test.loc[test[plant_col] == plant_id, "raw_nwp_forecast"] = plant_mean
            continue

        # Drop rows with NaN in features or target
        tr_clean = tr[feature_cols + [actual_col]].dropna()
        te_clean = te[feature_cols].copy()
        te_nan_mask = te_clean.isna().any(axis=1)

        if len(tr_clean) < 10:
            plant_mean = tr[actual_col].mean()
            test.loc[test[plant_col] == plant_id, "raw_nwp_forecast"] = plant_mean
            continue

        X_train = tr_clean[feature_cols].values
        y_train = tr_clean[actual_col].values

        model = LinearRegression()
        model.fit(X_train, y_train)
        models[plant_id] = model

        # Predict on test rows where features are not NaN
        valid_idx = te[~te_nan_mask].index
        if len(valid_idx) > 0:
            X_test = te.loc[valid_idx, feature_cols].values
            preds  = model.predict(X_test)
            preds  = np.clip(preds, 0, None)  # generation can't be negative
            test.loc[valid_idx, "raw_nwp_forecast"] = preds

        # Fill any remaining NaN with plant mean
        nan_idx = test[(test[plant_col] == plant_id) &
                       (test["raw_nwp_forecast"].isna())].index
        if len(nan_idx) > 0:
            test.loc[nan_idx, "raw_nwp_forecast"] = tr[actual_col].mean()

    return test, models


# ══════════════════════════════════════════════════════════════════════════════
# UNCERTAINTY WRAPPER
# Give each baseline a synthetic P10/P90 interval so we can compute CRPS.
# We use the historical residual std from the training set as the spread.
# This is honest: we're not cheating, just asking "if this baseline had
# confidence intervals, how wide would they need to be to be calibrated?"
# ══════════════════════════════════════════════════════════════════════════════

def add_baseline_intervals(test_df: pd.DataFrame,
                            train_df: pd.DataFrame,
                            forecast_col: str,
                            actual_col: str = "actual_mw",
                            plant_col: str = "plant_id",
                            confidence: float = 0.80) -> pd.DataFrame:
    """
    Adds synthetic P10/P90 intervals to a baseline forecast.

    Method: for each plant, compute the standard deviation of
    (actual - forecast) on the TRAINING set. Use that as sigma.
    Then P10 = forecast - 1.28*sigma, P90 = forecast + 1.28*sigma.
    (1.28 is the z-score for an 80% interval.)

    This is done so we can compute CRPS for baselines — it gives them
    the benefit of the doubt (calibrated intervals), making the comparison
    fair. If our model beats baselines even under this charitable assumption,
    the win is genuine.
    """
    test  = test_df.copy()
    train = train_df.copy()

    z = 1.2816  # norm.ppf(0.90) — z-score for 80% interval

    p10_col = forecast_col.replace("_forecast", "_p10")
    p90_col = forecast_col.replace("_forecast", "_p90")

    test[p10_col] = np.nan
    test[p90_col] = np.nan

    for plant_id in test[plant_col].unique():
        tr = train[train[plant_col] == plant_id]

        # Compute residual std from training set if forecast_col exists in train
        if forecast_col in tr.columns:
            residuals = tr[actual_col] - tr[forecast_col]
            sigma = residuals.std()
        else:
            # Fallback: use 20% of mean actual as sigma
            sigma = tr[actual_col].mean() * 0.20

        sigma = max(sigma, 0.5)  # minimum spread of 0.5 MW

        mask = test[plant_col] == plant_id
        test.loc[mask, p10_col] = (test.loc[mask, forecast_col] - z * sigma).clip(lower=0)
        test.loc[mask, p90_col] = test.loc[mask, forecast_col] + z * sigma

    return test


# ══════════════════════════════════════════════════════════════════════════════
# EVALUATE ONE BASELINE — shared helper used by run_all_baselines()
# ══════════════════════════════════════════════════════════════════════════════

def _evaluate_baseline(df: pd.DataFrame,
                        forecast_col: str,
                        actual_col: str = "actual_mw",
                        plant_type_col: str = "plant_type",
                        include_coverage_90: bool = False) -> dict:
    """
    Compute nMAE, nRMSE, CRPS for solar plants, wind plants, and overall.
    Rows where forecast is NaN (e.g. first 24h of persistence) are excluded.
    """
    df = df[df[forecast_col].notna()].copy()

    p10_col = forecast_col.replace("_forecast", "_p10")
    p90_col = forecast_col.replace("_forecast", "_p90")

    has_intervals = p10_col in df.columns and p90_col in df.columns

    def _stats(sub):
        if len(sub) == 0:
            return {}
        a = sub[actual_col].values
        f = sub[forecast_col].values
        result = {
            "n_samples": int(len(sub)),
            "nmae"     : round(nmae(a, f),  4),
            "nrmse"    : round(nrmse(a, f), 4),
        }
        if has_intervals:
            p10 = sub[p10_col].values
            p90 = sub[p90_col].values
            result["coverage_80"] = round(prediction_interval_coverage(a, p10, p90), 4)
            result["crps"] = round(crps_ensemble_score(a, f, p10, p90), 4)
            if "capacity_mw" in sub.columns:
                sharp = sharpness_score(p10, p90, sub["capacity_mw"].values)
                result["sharpness"] = round(sharp, 4) if not np.isnan(sharp) else None
            if include_coverage_90 and {"p05", "p95"}.issubset(sub.columns):
                result["coverage_90"] = round(
                    prediction_interval_coverage(a, sub["p05"].values, sub["p95"].values),
                    4,
                )
        return result

    solar = df[df[plant_type_col] == "solar"] if plant_type_col in df.columns else pd.DataFrame()
    wind  = df[df[plant_type_col] == "wind"]  if plant_type_col in df.columns else pd.DataFrame()

    return {
        "overall"      : _stats(df),
        "solar_summary": _stats(solar),
        "wind_summary" : _stats(wind),
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT — run_all_baselines()
# This is what metrics.py's get_results() will call on Day 3.
# ══════════════════════════════════════════════════════════════════════════════

def run_all_baselines(feature_path: str = FEATURE_MATRIX_PATH,
                      raw_weather_path: str = RAW_WEATHER_PATH) -> dict:
    """
    Load Person 1's data, run all three baselines, return results.

    Uses feature_matrix_final.csv as the primary source.
    Merges raw_weather_data.csv for GHI + wind_speed (needed by Raw NWP LR baseline).

    Parameters
    ----------
    feature_path    : path to feature_matrix_final.csv
    raw_weather_path: path to raw_weather_data.csv
    """
    import os
    print(f"[Baselines] Loading feature matrix from {feature_path}")
    df = pd.read_csv(feature_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Rename actual_generation_mw -> actual_mw (our internal name)
    df = df.rename(columns={"actual_generation_mw": "actual_mw"})

    # Cap nwp_spread outliers if the column exists
    # (values above 100 are numerical artifacts in Person 1's data)
    if "nwp_spread" in df.columns:
        df["nwp_spread"] = df["nwp_spread"].clip(upper=100.0)

    # Add plant_type from PLANT_TYPE_MAP if not already present
    if "plant_type" not in df.columns:
        df["plant_type"] = df["plant_id"].map(PLANT_TYPE_MAP).fillna("unknown")

    # Merge raw weather columns (GHI, wind_speed) for the NWP LR baseline
    # These live in raw_weather_data.csv, not in feature_matrix_final.csv
    if os.path.exists(raw_weather_path):
        print(f"[Baselines] Merging raw weather from {raw_weather_path}")
        rw = pd.read_csv(raw_weather_path)
        rw["timestamp"] = pd.to_datetime(rw["timestamp"], utc=True)
        rw = rw.rename(columns={"generation_mw": "actual_mw_raw"})
        rw = rw[["timestamp", "plant_id", "GHI", "wind_speed"]].copy()
        df = df.merge(rw, on=["timestamp", "plant_id"], how="left")
        # Rename to lowercase for our internal use
        df = df.rename(columns={"GHI": "ghi", "wind_speed": "wind_speed"})
    else:
        print(f"[Baselines] raw_weather_data.csv not found — Raw NWP LR will fall back to plant mean")
        df["ghi"]        = np.nan
        df["wind_speed"] = np.nan

    # Temporal split — same boundaries as metrics.py
    train_df, val_df, test_df = temporal_split(df, timestamp_col="timestamp")

    print("[Baselines] Running Persistence...")
    full_with_persistence = persistence_forecast(df, actual_col="actual_mw")
    test_with_persistence = full_with_persistence[
        full_with_persistence["timestamp"] >= test_df["timestamp"].min()
    ].copy()
    test_with_persistence = add_baseline_intervals(
        test_with_persistence, train_df, "persistence_forecast", actual_col="actual_mw"
    )
    persistence_results = _evaluate_baseline(test_with_persistence, "persistence_forecast",
                                              actual_col="actual_mw")

    print("[Baselines] Running Climatological Mean...")
    test_with_clim  = climatological_forecast(train_df, test_df.copy(), actual_col="actual_mw")
    train_with_clim = climatological_forecast(train_df, train_df.copy(), actual_col="actual_mw")
    test_with_clim  = add_baseline_intervals(
        test_with_clim, train_with_clim, "climatological_forecast", actual_col="actual_mw"
    )
    climatological_results = _evaluate_baseline(test_with_clim, "climatological_forecast",
                                                 actual_col="actual_mw")

    print("[Baselines] Running Raw NWP Linear Regression...")
    test_with_nwp,  _  = raw_nwp_lr_forecast(train_df, test_df.copy(),
                                               actual_col="actual_mw")
    train_with_nwp, _  = raw_nwp_lr_forecast(train_df, train_df.copy(),
                                               actual_col="actual_mw")
    test_with_nwp = add_baseline_intervals(
        test_with_nwp, train_with_nwp, "raw_nwp_forecast", actual_col="actual_mw"
    )
    raw_nwp_results = _evaluate_baseline(test_with_nwp, "raw_nwp_forecast",
                                          actual_col="actual_mw")

    print("[Baselines] Done.")
    return {
        "persistence"   : persistence_results,
        "climatological": climatological_results,
        "raw_nwp"       : raw_nwp_results,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC DATA GENERATOR
# Generates realistic dummy data so we can run and test baselines right now,
# WITHOUT waiting for Person 1's real CSV.
# This is ONLY used for testing — it is NOT training data.
# ══════════════════════════════════════════════════════════════════════════════

def generate_dummy_dataset(n_days: int = 365, seed: int = 42) -> pd.DataFrame:
    """
    Generates a realistic synthetic dataset for testing baselines.

    Mimics what Person 1's CSV will look like:
      - 6 plants: 3 solar (PVG_S1, PVG_S2, MIX_S1), 3 wind (GDG_W1, GDG_W2, MIX_W1)
      - Hourly resolution
      - Solar generation follows a bell curve peaking at noon
      - Wind generation is random but temporally correlated
      - Includes raw weather features (ghi, temperature, wind_speed)
    """
    np.random.seed(seed)
    dates = pd.date_range("2023-01-01", periods=n_days * 24, freq="h")

    plants = {
        "PVG_S1": ("solar", 100),
        "PVG_S2": ("solar",  80),
        "MIX_S1": ("solar",  60),
        "GDG_W1": ("wind",   50),
        "GDG_W2": ("wind",   40),
        "MIX_W1": ("wind",   30),
    }

    rows = []
    for plant_id, (ptype, capacity) in plants.items():
        for i, ts in enumerate(dates):
            h     = ts.hour
            doy   = ts.day_of_year
            month = ts.month

            # Seasonal factor (stronger in summer for solar, more uniform for wind)
            season_factor = 1.0 + 0.3 * np.sin(2 * np.pi * (doy - 80) / 365)

            if ptype == "solar":
                # Bell curve: zero at night, peaks at noon
                if 6 <= h <= 18:
                    solar_fraction = np.sin(np.pi * (h - 6) / 12)
                else:
                    solar_fraction = 0.0
                cloud_noise  = np.random.uniform(0.6, 1.0)
                ghi          = 1000 * solar_fraction * season_factor * cloud_noise
                temperature  = 25 + 8 * np.sin(np.pi * (h - 4) / 12) + 3 * season_factor + np.random.normal(0, 1)
                actual_mw    = capacity * solar_fraction * season_factor * cloud_noise + np.random.normal(0, 1)
                actual_mw    = float(np.clip(actual_mw, 0, capacity))
                row = {
                    "timestamp"  : ts,
                    "plant_id"   : plant_id,
                    "plant_type" : ptype,
                    "actual_mw"  : round(actual_mw, 3),
                    "ghi"        : round(float(np.clip(ghi, 0, 1200)), 2),
                    "temperature": round(float(temperature), 2),
                    "wind_speed" : float(np.random.uniform(1, 6)),
                }
            else:
                # Wind: auto-correlated random walk
                wind_speed  = float(np.clip(
                    8 + 5 * np.sin(2 * np.pi * doy / 365) + np.random.normal(0, 3), 0, 30
                ))
                # Simplified power curve
                if wind_speed < 3:
                    wind_fraction = 0.0
                elif wind_speed < 12:
                    wind_fraction = (wind_speed - 3) / 9
                elif wind_speed <= 25:
                    wind_fraction = 1.0
                else:
                    wind_fraction = 0.0
                actual_mw = capacity * wind_fraction + np.random.normal(0, 1)
                actual_mw = float(np.clip(actual_mw, 0, capacity))
                row = {
                    "timestamp"  : ts,
                    "plant_id"   : plant_id,
                    "plant_type" : ptype,
                    "actual_mw"  : round(actual_mw, 3),
                    "ghi"        : 0.0,
                    "temperature": round(25.0 + np.random.normal(0, 2), 2),
                    "wind_speed" : round(wind_speed, 2),
                }

            rows.append(row)

    return pd.DataFrame(rows)