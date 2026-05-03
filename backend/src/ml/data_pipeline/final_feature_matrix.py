"""
Day 3 — Part 2: Final Feature Matrix Assembly

Takes the Day 2 feature matrix and adds:
  - nwp_spread (NWP ensemble spread — atmospheric uncertainty)

Final feature matrix columns for Person 2:
  timestamp, plant_id, plant_type, cluster_id,
  CMF,                     ← primary solar feature
  power_curve_fraction,    ← primary wind feature
  temperature,
  nwp_spread,              ← NEW: atmospheric uncertainty signal
  capacity_mw,
  lat_sin, lat_cos,
  lon_sin, lon_cos,
  tilt_angle_deg,
  hub_height_m,
  hour_sin, hour_cos,
  doy_sin,  doy_cos,
  season,
  actual_generation_mw     ← target variable

Total: 21 columns (was 20, now +nwp_spread)

Why nwp_spread matters:
  Person 2's CQR uncertainty layer uses nwp_spread as a feature.
  High spread → model produces wide P10/P90 intervals automatically.
  Low spread  → narrow intervals, tight scheduling is safe.
  This is what makes uncertainty physically meaningful, not just statistical.
"""

import numpy as np
import pandas as pd
import os
import sys


from nwp_ensemble import add_nwp_spread_to_dataframe

np.random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data")


def assemble_final_feature_matrix(df_day2, raw_physics_df):
    """
    Adds NWP spread to the Day 2 feature matrix.
    Returns the complete 21-column feature matrix.
    """

    print("Adding NWP ensemble spread...")
    df = add_nwp_spread_to_dataframe(df_day2, raw_physics_df)

    # Final column order — exactly what Person 2 gets
    final_cols = [
        "timestamp",
        "plant_id",
        "plant_type",
        "cluster_id",
        # Physics features
        "CMF",
        "power_curve_fraction",
        # Weather
        "temperature",
        "nwp_spread",           # NEW
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
        # Target
        "actual_generation_mw",
    ]

    df = df[final_cols].copy()
    # Drop any extra columns that leaked in during validation steps
    df = df[[c for c in final_cols if c in df.columns]]
    return df


def validate_nwp_spread(df, raw_physics_df):
    """
    Verifies nwp_spread has the right physical behaviour.
    Prints PASS/FAIL for each check.
    """
    results = []

    def check(name, condition, detail=""):
        marker = "OK" if condition else "!!"
        print(f"  [{marker}] {name}")
        if detail:
            print(f"       {detail}")
        results.append(condition)
        return condition

    print("\n--- NWP spread validation ---")

    solar = df[df["plant_type"] == "solar"]
    wind  = df[df["plant_type"] == "wind"]

    check("nwp_spread column exists", "nwp_spread" in df.columns)
    check("nwp_spread >= 0 always",
          (df["nwp_spread"] >= 0).all(),
          f"Min: {df['nwp_spread'].min():.4f}")

    # Solar nighttime spread must be zero
    solar_night = solar[solar["CMF"] == 0]
    check("Solar NWP spread = 0 at night",
          (solar_night["nwp_spread"] == 0).all(),
          f"Non-zero night spread: {(solar_night['nwp_spread'] > 0).sum()}")

    # Monsoon spread should be larger than winter spread (more cloud uncertainty)
    df["month"] = pd.to_datetime(df["timestamp"]).dt.month
    monsoon_spread = df.loc[
        (df["plant_type"]=="solar") & df["month"].isin([6,7,8,9]), "nwp_spread"
    ].mean()
    winter_spread = df.loc[
        (df["plant_type"]=="solar") & df["month"].isin([12,1,2]), "nwp_spread"
    ].mean()
    check("Monsoon solar spread > winter solar spread",
          monsoon_spread > winter_spread,
          f"Monsoon: {monsoon_spread:.2f} W/m², Winter: {winter_spread:.2f} W/m²")

    # Wind spread should be positive during operating hours
    wind_operating = wind[wind["power_curve_fraction"] > 0]
    check("Wind NWP spread > 0 during operating hours",
          (wind_operating["nwp_spread"] > 0).all(),
          f"Zero-spread operating rows: {(wind_operating['nwp_spread']==0).sum()}")

    # No NaN
    check("No NaN in nwp_spread",
          df["nwp_spread"].isna().sum() == 0,
          f"NaN count: {df['nwp_spread'].isna().sum()}")

    # Spread should be higher on cloudy days vs clear days (solar)
    raw_solar = raw_physics_df[raw_physics_df["plant_type"] == "solar"]
    solar_merged = solar.copy().reset_index(drop=True)
    raw_solar_reset = raw_solar.reset_index(drop=True)

    # Use cloud_cover from raw data to split clear vs cloudy daytime
    cloudy_idx = raw_solar_reset[
        (raw_solar_reset["cloud_cover"] > 0.6) &
        (raw_solar_reset["clearsky_GHI"] >= 5)
    ].index
    clear_idx = raw_solar_reset[
        (raw_solar_reset["cloud_cover"] < 0.2) &
        (raw_solar_reset["clearsky_GHI"] >= 5)
    ].index

    if len(cloudy_idx) > 0 and len(clear_idx) > 0:
        cloudy_spread = solar_merged.loc[
            solar_merged.index.isin(cloudy_idx), "nwp_spread"
        ].mean()
        clear_spread = solar_merged.loc[
            solar_merged.index.isin(clear_idx), "nwp_spread"
        ].mean()
        check("Cloudy solar spread > clear sky solar spread",
              cloudy_spread > clear_spread,
              f"Cloudy: {cloudy_spread:.2f} W/m², Clear: {clear_spread:.2f} W/m²")

    passed = sum(results)
    total  = len(results)
    print(f"\n  {passed}/{total} NWP spread checks passed.")
    return passed == total


if __name__ == "__main__":
    print("Testing final feature matrix assembly...")
    df_day2 = pd.read_csv(os.path.join(DATA_DIR, "feature_matrix.csv"))
    raw     = pd.read_csv(os.path.join(DATA_DIR, "raw_with_physics.csv"))
    df_final = assemble_final_feature_matrix(df_day2, raw)
    print(f"Shape: {df_final.shape}")
    print(f"Columns: {list(df_final.columns)}")