"""
Day 1 main entry point.
Run: python main_day1.py

Outputs (all in data/):
  - asset_registry.csv
  - seed_solar.csv
  - seed_wind.csv
  - raw_weather_data.csv
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "ml", "data_pipeline"))
import numpy as np
import pandas as pd

# Reproducibility
np.random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

print("=" * 60)
print("KREDL/KSPDCL — Day 1: Synthetic Data Generation")
print("=" * 60)

# Step 1: Asset registry
print("\n[1/3] Building asset registry...")
from asset_registry import get_registry_df
registry = get_registry_df()
registry.to_csv(os.path.join(DATA_DIR, "asset_registry.csv"), index=False)
print(registry[["plant_id","type","cluster_id","capacity_mw","latitude","longitude"]].to_string(index=False))

# Step 2: Seed data from NASA POWER (or synthetic fallback)
print("\n[2/3] Getting seed data for copula fitting...")
from fetch_nasa_power import get_seed_data
solar_seed, wind_seed = get_seed_data(save_dir=DATA_DIR)

# Step 3: Generate full synthetic dataset
print("\n[3/3] Generating 8760h × 6 plants via Gaussian Copula...")
from generate_data import generate_all_plants
df = generate_all_plants(solar_seed, wind_seed, save_dir=DATA_DIR)

# Summary report
print("\n" + "=" * 60)
print("Day 1 Complete — Summary")
print("=" * 60)

print(f"\nTotal rows: {len(df):,}")
print(f"Total plants: {df['plant_id'].nunique()}")
print(f"Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")

print("\nGeneration by plant (MW):")
summary = df.groupby(["plant_id","plant_type","cluster_id"])["generation_mw"].agg(
    mean="mean", max="max", min="min"
).round(2)
print(summary.to_string())

print("\nSolar plant GHI stats:")
solar_df = df[df["plant_type"] == "solar"]
print(solar_df.groupby("plant_id")["GHI"].describe().round(1).to_string())

print("\nWind plant wind speed stats:")
wind_df = df[df["plant_type"] == "wind"]
print(wind_df.groupby("plant_id")["wind_speed"].describe().round(2).to_string())

print("\nSeason distribution (all plants):")
season_names = {0: "winter", 1: "summer", 2: "monsoon", 3: "post-monsoon"}
season_counts = df.drop_duplicates("timestamp")["season"].map(season_names).value_counts()
print(season_counts.to_string())

print("\nOutputs saved to data/:")
for f in os.listdir(DATA_DIR):
    size = os.path.getsize(os.path.join(DATA_DIR, f)) / 1024
    print(f"  {f}  ({size:.1f} KB)")

print("\nDay 1 done. Hand off seed data to Day 2 (physics transforms).")