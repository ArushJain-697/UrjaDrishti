"""
Day 2 — Part 3: Feature Matrix Builder

Takes:
  - raw_weather_data.csv  (Day 1 output)
  - clearsky + CMF        (from clearsky_cmf.py)
  - power curve fraction  (from power_curve.py)

Produces:
  - feature_matrix.csv    (handoff to Person 2)

Feature matrix columns:
  timestamp, plant_id, plant_type, cluster_id,
  CMF,                        ← primary solar feature (replaces raw GHI)
  power_curve_fraction,       ← primary wind feature (replaces raw wind speed)
  temperature,
  capacity_mw,
  lat_sin, lat_cos,           ← geographic encoding
  lon_sin, lon_cos,
  tilt_angle_deg,             ← solar geometry metadata
  hub_height_m,               ← wind turbine metadata
  hour_sin, hour_cos,         ← cyclical time encoding
  doy_sin, doy_cos,
  season,
  actual_generation_mw        ← target variable for Person 2
"""

import numpy as np
import pandas as pd
import os
import sys

# Add day1 path so we can import asset_registry


def add_cyclical_encodings(df):
    """
    Encode hour-of-day and day-of-year as sin/cos pairs.
    Raw integers must never enter the model — hour 23 is not 'far from' hour 0.
    """
    ts = pd.to_datetime(df["timestamp"])

    df["hour_sin"] = np.sin(2 * np.pi * ts.dt.hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * ts.dt.hour / 24)
    df["doy_sin"]  = np.sin(2 * np.pi * ts.dt.dayofyear / 365)
    df["doy_cos"]  = np.cos(2 * np.pi * ts.dt.dayofyear / 365)

    return df


def add_geographic_encodings(df, registry_df):
    """
    Encode latitude and longitude as sin/cos.
    Raw lat/lon are not great features — encoding preserves spatial proximity.
    Also merges tilt_angle and hub_height from the asset registry.
    """
    # Merge asset metadata
    meta = registry_df[["plant_id", "latitude", "longitude",
                         "tilt_angle_deg", "hub_height_m"]].copy()
    df = df.merge(meta, on="plant_id", how="left")

    # Geographic sin/cos
    df["lat_sin"] = np.sin(np.deg2rad(df["latitude"]))
    df["lat_cos"] = np.cos(np.deg2rad(df["latitude"]))
    df["lon_sin"] = np.sin(np.deg2rad(df["longitude"]))
    df["lon_cos"] = np.cos(np.deg2rad(df["longitude"]))

    # Drop raw lat/lon — not needed downstream
    df = df.drop(columns=["latitude", "longitude"])

    return df


def build_feature_matrix(df_with_physics, registry_df):
    """
    Assembles the final feature matrix from the physics-enriched DataFrame.

    Parameters
    ----------
    df_with_physics : DataFrame — has CMF and power_curve_fraction columns
    registry_df     : DataFrame — asset registry from Day 1

    Returns
    -------
    DataFrame — feature matrix ready for Person 2
    """
    df = df_with_physics.copy()

    # Add encodings
    df = add_cyclical_encodings(df)
    df = add_geographic_encodings(df, registry_df)

    # Fill cross-type NaNs with 0 — cleaner for tree models
    # Solar plants: power_curve_fraction = 0 (they don't have turbines)
    # Wind plants:  CMF = 0, tilt_angle = 0 (they don't have panels)
    df["CMF"]                  = df["CMF"].fillna(0.0)
    df["power_curve_fraction"] = df["power_curve_fraction"].fillna(0.0)
    df["tilt_angle_deg"]       = df["tilt_angle_deg"].fillna(0.0)
    df["hub_height_m"]         = df["hub_height_m"].fillna(0.0)

    # Nighttime CMF: was NaN (meaningless), set to 0 for model
    # (GHI=0 at night → CMF=0 makes sense: 0% of potential being captured)
    # Already handled above by fillna, but make explicit for clarity
    solar_mask = df["plant_type"] == "solar"
    night_mask = df["GHI"] == 0.0
    df.loc[solar_mask & night_mask, "CMF"] = 0.0

    # Select and order final columns
    feature_cols = [
        # Identity
        "timestamp",
        "plant_id",
        "plant_type",
        "cluster_id",
        # Primary physics features
        "CMF",
        "power_curve_fraction",
        # Weather
        "temperature",
        # Asset metadata
        "capacity_mw",
        "lat_sin",
        "lat_cos",
        "lon_sin",
        "lon_cos",
        "tilt_angle_deg",
        "hub_height_m",
        # Cyclical time
        "hour_sin",
        "hour_cos",
        "doy_sin",
        "doy_cos",
        # Season
        "season",
        # Target (what Person 2 is predicting)
        "actual_generation_mw",
    ]

    # Rename generation column to match expected name
    df = df.rename(columns={"generation_mw": "actual_generation_mw"})

    # Keep only feature columns
    df_features = df[feature_cols].copy()

    return df_features


def validate_feature_matrix(df):
    """
    Quick sanity checks on the feature matrix before handing off.
    Prints PASS/FAIL for each check.
    """
    print("\n--- Feature matrix validation ---")
    issues = 0

    def check(name, condition, detail=""):
        nonlocal issues
        marker = "OK" if condition else "!!"
        print(f"  [{marker}] {name}")
        if detail:
            print(f"       {detail}")
        if not condition:
            issues += 1

    check("Shape is (52560, 20)",
          df.shape == (52560, 20),
          f"Actual: {df.shape}")

    check("CMF in [0, 1]",
          df["CMF"].between(0, 1).all(),
          f"Range: {df['CMF'].min():.4f}–{df['CMF'].max():.4f}")

    check("power_curve_fraction in [0, 1]",
          df["power_curve_fraction"].between(0, 1).all(),
          f"Range: {df['power_curve_fraction'].min():.4f}–{df['power_curve_fraction'].max():.4f}")

    check("No NaN in CMF",
          df["CMF"].isna().sum() == 0,
          f"NaN count: {df['CMF'].isna().sum()}")

    check("No NaN in power_curve_fraction",
          df["power_curve_fraction"].isna().sum() == 0,
          f"NaN count: {df['power_curve_fraction'].isna().sum()}")

    check("No NaN in hour_sin / hour_cos",
          df[["hour_sin","hour_cos"]].isna().sum().sum() == 0)

    check("No NaN in actual_generation_mw",
          df["actual_generation_mw"].isna().sum() == 0)

    check("actual_generation_mw >= 0",
          (df["actual_generation_mw"] >= 0).all(),
          f"Min: {df['actual_generation_mw'].min():.4f}")

    check("Solar CMF is 0 at night",
          (df.loc[(df["plant_type"]=="solar") &
                  (df["actual_generation_mw"]==0), "CMF"] == 0).all())

    check("Wind CMF is 0 (wind plants have no GHI)",
          (df.loc[df["plant_type"]=="wind", "CMF"] == 0).all())

    check("Solar power_curve_fraction is 0 (solar has no turbine)",
          (df.loc[df["plant_type"]=="solar", "power_curve_fraction"] == 0).all())

    check("hour_sin at midnight ≈ 0",
          abs(df[df["timestamp"].astype(str).str.contains("00:00")]["hour_sin"].iloc[0]) < 0.01,
          f"Actual: {df[df['timestamp'].astype(str).str.contains('00:00')]['hour_sin'].iloc[0]:.6f}")

    # Cyclical continuity: sin²+cos² should always = 1
    err_h = ((df["hour_sin"]**2 + df["hour_cos"]**2) - 1).abs().max()
    err_d = ((df["doy_sin"]**2  + df["doy_cos"]**2)  - 1).abs().max()
    check("sin²+cos²=1 for hour encoding (cyclical correctness)",
          err_h < 1e-10,
          f"Max error: {err_h:.2e}")
    check("sin²+cos²=1 for doy encoding (cyclical correctness)",
          err_d < 1e-10,
          f"Max error: {err_d:.2e}")

    if issues == 0:
        print(f"\n  All checks passed. Feature matrix is clean.")
    else:
        print(f"\n  {issues} check(s) failed. Fix before handing off.")

    return issues == 0


if __name__ == "__main__":
    # Quick test
    import pandas as pd
    df = pd.DataFrame({
        "timestamp": pd.date_range("2023-01-01", periods=4, freq="h", tz="Asia/Kolkata"),
        "plant_id": ["PVG_S1"]*4,
        "plant_type": ["solar"]*4,
        "cluster_id": ["C1"]*4,
        "GHI": [0, 500, 800, 0],
        "CMF": [0.0, 0.8, 0.9, 0.0],
        "power_curve_fraction": [0.0]*4,
        "temperature": [25.0]*4,
        "capacity_mw": [150]*4,
        "generation_mw": [0, 60, 80, 0],
        "season": [0]*4,
    })
    print("Feature matrix builder loaded OK.")