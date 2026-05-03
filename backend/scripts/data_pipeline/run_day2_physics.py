"""
Day 2 main entry point.
Run: python main_day2.py

Reads:   data/raw_weather_data.csv  (Day 1 output)
Reads:   data/asset_registry.csv

Produces:
  data/feature_matrix.csv          ← handoff to Person 2
  data/raw_with_physics.csv        ← intermediate (for your own debugging)

What this script does:
  1. Loads Day 1 raw data
  2. Runs Ineichen-Perez clear-sky model for all solar plants
  3. Derives CMF for all solar plants
  4. Applies Suzlon S111 power curve transform for all wind plants
  5. Adds cyclical time encodings and geographic encodings
  6. Assembles and validates the feature matrix
  7. Saves feature_matrix.csv for Person 2
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "ml", "data_pipeline"))
import numpy as np
import pandas as pd

# Make Day 1 modules importable

from clearsky_cmf  import process_all_solar_plants
from power_curve   import process_all_wind_plants, print_curve_table
from feature_matrix import build_feature_matrix, validate_feature_matrix

np.random.seed(42)

print("=" * 60)
print("KREDL/KSPDCL — Day 2: Physics Transforms")
print("=" * 60)

# ------------------------------------------------------------------
# Load Day 1 outputs
# ------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")

print(f"\n[1/5] Loading Day 1 data from {DATA_DIR}...")
df_raw  = pd.read_csv(os.path.join(DATA_DIR, "raw_weather_data.csv"))
registry = pd.read_csv(os.path.join(DATA_DIR, "asset_registry.csv"))

print(f"  Loaded {len(df_raw):,} rows, {df_raw['plant_id'].nunique()} plants")

# ------------------------------------------------------------------
# Ineichen-Perez + CMF for solar plants
# ------------------------------------------------------------------
print("\n[2/5] Computing clear-sky GHI (Ineichen-Perez) and CMF...")
df = process_all_solar_plants(df_raw)

# Quick check on CMF distribution
solar = df[df["plant_type"] == "solar"]
day_solar = solar[solar["clearsky_GHI"] >= 5]
print(f"\n  CMF daytime distribution (all solar plants):")
print(f"    Mean: {day_solar['CMF'].mean():.3f}")
print(f"    Std:  {day_solar['CMF'].std():.3f}")
print(f"    Clear sky hours (CMF>0.8): "
      f"{(day_solar['CMF'] > 0.8).sum():,}")
print(f"    Heavy cloud hours (CMF<0.3): "
      f"{(day_solar['CMF'] < 0.3).sum():,}")

# ------------------------------------------------------------------
# Power curve transform for wind plants
# ------------------------------------------------------------------
print("\n[3/5] Applying turbine power curve transform (Suzlon S111)...")
print_curve_table()
print()
df = process_all_wind_plants(df)

# ------------------------------------------------------------------
# Build feature matrix
# ------------------------------------------------------------------
print("\n[4/5] Building feature matrix...")
df_features = build_feature_matrix(df, registry)

print(f"  Feature matrix shape: {df_features.shape}")
print(f"  Columns: {list(df_features.columns)}")

# ------------------------------------------------------------------
# Validate
# ------------------------------------------------------------------
print("\n[5/5] Validating feature matrix...")
ok = validate_feature_matrix(df_features)

# ------------------------------------------------------------------
# Save outputs
# ------------------------------------------------------------------
os.makedirs(os.path.join(DATA_DIR), exist_ok=True)

# Intermediate file (your debugging reference — not handed to Person 2)
intermediate_path = os.path.join(DATA_DIR, "raw_with_physics.csv")
df.to_csv(intermediate_path, index=False)
print(f"\n  Saved intermediate (with clearsky_GHI): raw_with_physics.csv")

# Final handoff file
handoff_path = os.path.join(DATA_DIR, "feature_matrix.csv")
df_features.to_csv(handoff_path, index=False)
print(f"  Saved feature matrix: feature_matrix.csv")

# ------------------------------------------------------------------
# Final summary
# ------------------------------------------------------------------
print("\n" + "=" * 60)
print("Day 2 Complete — Summary")
print("=" * 60)

print("\nFeature matrix sample (first 5 rows, key columns):")
cols_show = ["timestamp","plant_id","plant_type","CMF",
             "power_curve_fraction","temperature","hour_sin","season",
             "actual_generation_mw"]
print(df_features[cols_show].head(5).to_string(index=False))

print("\nCMF statistics by plant (daytime only):")
day_mask = df_features["CMF"] > 0
solar_f  = df_features[df_features["plant_type"] == "solar"]
day_solar_f = solar_f[solar_f["CMF"] > 0]
print(day_solar_f.groupby("plant_id")["CMF"].describe().round(3).to_string())

print("\nPower curve fraction statistics by wind plant:")
wind_f = df_features[df_features["plant_type"] == "wind"]
op_wind = wind_f[wind_f["power_curve_fraction"] > 0]
print(op_wind.groupby("plant_id")["power_curve_fraction"].describe().round(3).to_string())

print("\nFiles in data/:")
for f in sorted(os.listdir(DATA_DIR)):
    size = os.path.getsize(os.path.join(DATA_DIR, f)) / 1024
    print(f"  {f}  ({size:.1f} KB)")

status = "READY — hand off feature_matrix.csv to Person 2." if ok else \
         "ISSUES FOUND — fix before handing off."
print(f"\nStatus: {status}")