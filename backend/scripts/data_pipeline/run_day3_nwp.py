"""
Day 3 main entry point.
Run: python main_day3.py

Reads:
  day1/data/feature_matrix.csv      (Day 2 output)
  day1/data/raw_with_physics.csv    (Day 2 intermediate)

Produces:
  day1/data/feature_matrix_final.csv   ← complete handoff to Person 2
                                          21 columns, ready for LightGBM

What this does:
  1. Loads Day 2 feature matrix
  2. Simulates NWP ensemble spread for all 6 plants
  3. Assembles and validates the final 21-column feature matrix
  4. Saves feature_matrix_final.csv
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "ml", "data_pipeline"))
import numpy as np
import pandas as pd


from final_feature_matrix import assemble_final_feature_matrix, validate_nwp_spread

np.random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")

print("=" * 60)
print("KREDL/KSPDCL — Day 3: NWP Ensemble Spread")
print("=" * 60)

# ------------------------------------------------------------------
# Load Day 2 outputs
# ------------------------------------------------------------------
print(f"\n[1/4] Loading Day 2 outputs from {DATA_DIR}...")
df_day2  = pd.read_csv(os.path.join(DATA_DIR, "feature_matrix.csv"))
raw      = pd.read_csv(os.path.join(DATA_DIR, "raw_with_physics.csv"))
print(f"  Feature matrix: {df_day2.shape}")
print(f"  Raw with physics: {raw.shape}")

# ------------------------------------------------------------------
# Add NWP ensemble spread
# ------------------------------------------------------------------
print("\n[2/4] Simulating NWP ensemble spread (10 members per hour)...")
df_final = assemble_final_feature_matrix(df_day2, raw)

# ------------------------------------------------------------------
# Validate
# ------------------------------------------------------------------
print("\n[3/4] Validating NWP spread behaviour...")
ok = validate_nwp_spread(df_final, raw)

# ------------------------------------------------------------------
# Save
# ------------------------------------------------------------------
print("\n[4/4] Saving final feature matrix...")
# Drop the month helper column added during summary — not a model feature
if "month" in df_final.columns:
    df_final = df_final.drop(columns=["month"])
if "season_name" in df_final.columns:
    df_final = df_final.drop(columns=["season_name"])
out_path = os.path.join(DATA_DIR, "feature_matrix_final.csv")
df_final.to_csv(out_path, index=False)
print(f"  Saved: feature_matrix_final.csv  "
      f"({os.path.getsize(out_path)/1024:.1f} KB)")

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
print("\n" + "=" * 60)
print("Day 3 Complete — Summary")
print("=" * 60)

print(f"\nFinal feature matrix: {df_final.shape[0]:,} rows × {df_final.shape[1]} columns")
print(f"Columns: {list(df_final.columns)}")

print("\nNWP spread by plant type and season:")
df_final["month"] = pd.to_datetime(df_final["timestamp"]).dt.month
season_map = {1:0,2:0,3:1,4:1,5:1,6:2,7:2,8:2,9:2,10:3,11:3,12:0}
season_names = {0:"winter",1:"summer",2:"monsoon",3:"post-monsoon"}
df_final["season_name"] = df_final["month"].map(season_map).map(season_names)

spread_summary = df_final.groupby(["plant_type","season_name"])["nwp_spread"].mean().round(3)
print(spread_summary.to_string())

print("\nNWP spread statistics (all plants):")
print(df_final.groupby("plant_type")["nwp_spread"].describe().round(3).to_string())

print("\nSample rows showing spread variation:")
cols = ["timestamp","plant_id","plant_type","CMF",
        "power_curve_fraction","nwp_spread","actual_generation_mw"]
# Show a clear hour, a cloudy hour, a stormy wind hour
sample_solar = df_final[
    (df_final["plant_type"]=="solar") &
    (df_final["actual_generation_mw"] > 0)
].nlargest(3, "nwp_spread")[cols]
sample_wind = df_final[
    (df_final["plant_type"]=="wind")
].nlargest(3, "nwp_spread")[cols]
print("\nTop spread hours — solar:")
print(sample_solar.to_string(index=False))
print("\nTop spread hours — wind:")
print(sample_wind.to_string(index=False))

status = "READY" if ok else "ISSUES FOUND"
print(f"\nStatus: {status}")
print("Hand off feature_matrix_final.csv to Person 2.")
print("Day 3 done — Day 4 is stress test scenario generation.")