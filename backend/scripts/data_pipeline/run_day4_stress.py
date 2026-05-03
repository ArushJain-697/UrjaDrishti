"""
Day 4 main entry point.
Run: python main_day4.py

Reads:   Nothing from previous days (self-contained)
Produces (all in day1/data/):
  stress_cloud_ramp.csv          — Scenario 1
  stress_monsoon_onset.csv       — Scenario 2
  stress_wind_spike.csv          — Scenario 3
  stress_low_irradiance.csv      — Scenario 4

All 4 files have the same 21 columns as feature_matrix_final.csv
+ extra columns: event_id, hour_in_event (and day_in_event for S2/S4)
+ wind_speed_ms for S3

Person 4 feeds these directly into the trained inference pipeline.
Expected behaviour:
  - Model accuracy degrades (higher nMAE than normal test set)
  - CQR intervals WIDEN visibly during stress events
  - Interval width should be 2-5x normal on worst hours
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "ml", "data_pipeline"))
import numpy as np
import pandas as pd


from stress_scenarios import generate_all_stress_scenarios

np.random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")

print("=" * 60)
print("KREDL/KSPDCL — Day 4: Stress Test Scenario Generation")
print("=" * 60)

# Generate all 4 scenarios
scenarios = generate_all_stress_scenarios(save_dir=DATA_DIR)

# ------------------------------------------------------------------
# Summary report
# ------------------------------------------------------------------
print("\n" + "=" * 60)
print("Day 4 Complete — Summary")
print("=" * 60)

s_names = {
    "cloud_ramp":       "Scenario 1 — Sudden Cloud Ramp",
    "monsoon_onset":    "Scenario 2 — Monsoon Onset",
    "wind_spike":       "Scenario 3 — Wind Speed Spike",
    "low_irradiance":   "Scenario 4 — Sustained Low Irradiance",
}

for key, df in scenarios.items():
    print(f"\n{s_names[key]}")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {df.shape[1]}")

    if "CMF" in df.columns:
        day = df[df["CMF"] > 0]
        if len(day) > 0:
            print(f"  CMF (daytime): mean={day['CMF'].mean():.3f}, "
                  f"min={day['CMF'].min():.3f}, max={day['CMF'].max():.3f}")
            print(f"  NWP spread (daytime): mean={day['nwp_spread'].mean():.2f}, "
                  f"max={day['nwp_spread'].max():.2f} W/m²")

    if key == "wind_spike":
        print(f"  Wind speed range: "
              f"{df['wind_speed_ms'].min():.1f}–{df['wind_speed_ms'].max():.1f} m/s")
        shutdown_rows = df[df["wind_speed_ms"] > 25]
        print(f"  Hours above cut-out (generation=0): {len(shutdown_rows)}")

print("\n--- What Person 4 does with these ---")
print("  Feed each CSV into the trained inference pipeline.")
print("  Measure nMAE per scenario vs normal holdout nMAE.")
print("  Plot P10/P90 interval width — should widen during stress events.")
print("  Verify CQR intervals contain actual values at ~80% rate even here.")

print("\nFiles in data/:")
stress_files = [f for f in os.listdir(DATA_DIR) if f.startswith("stress_")]
for f in sorted(stress_files):
    size = os.path.getsize(os.path.join(DATA_DIR, f)) / 1024
    print(f"  {f}  ({size:.1f} KB)")

print("\nDay 4 done.")
print("Hand stress_*.csv files to Person 4 along with feature_matrix_final.csv.")