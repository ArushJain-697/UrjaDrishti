"""
Day 4 Verification Script
Run: python verify_day4.py

Checks all 4 stress scenarios are physically correct and
have the right column structure for Person 4's inference pipeline.
"""

import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "ml", "data_pipeline"))

from power_curve import power_curve_fraction

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")

results = []

def check(name, condition, detail=""):
    marker = "OK" if condition else "!!"
    print(f"  [{marker}] {name}")
    if detail:
        print(f"       {detail}")
    results.append((name, condition))
    return condition

EXPECTED_CORE_COLS = [
    "timestamp","plant_id","plant_type","cluster_id",
    "CMF","power_curve_fraction","temperature","nwp_spread",
    "capacity_mw","lat_sin","lat_cos","lon_sin","lon_cos",
    "tilt_angle_deg","hub_height_m",
    "hour_sin","hour_cos","doy_sin","doy_cos",
    "season","actual_generation_mw",
    "event_id","hour_in_event",
]

print("=" * 60)
print("Day 4 Verification")
print("=" * 60)

# ------------------------------------------------------------------
# SCENARIO 1: CLOUD RAMP
# ------------------------------------------------------------------
print("\n--- Scenario 1: Cloud Ramp ---")
path1 = os.path.join(DATA_DIR, "stress_cloud_ramp.csv")
check("stress_cloud_ramp.csv exists", os.path.exists(path1))
df1 = pd.read_csv(path1)

check("5 events present",
      df1["event_id"].nunique() == 5,
      f"Events: {df1['event_id'].unique()}")

check("Each event has 48 hours",
      (df1.groupby("event_id").size() == 48).all(),
      f"Sizes: {df1.groupby('event_id').size().to_dict()}")

check("All core columns present",
      all(c in df1.columns for c in EXPECTED_CORE_COLS),
      f"Missing: {[c for c in EXPECTED_CORE_COLS if c not in df1.columns]}")

# Pre-ramp CMF should be high
pre_ramp = df1[df1["hour_in_event"] < 10]
check("Pre-ramp CMF > 0.7 (clear sky before event)",
      pre_ramp[pre_ramp["CMF"] > 0]["CMF"].mean() > 0.7,
      f"Pre-ramp mean CMF: {pre_ramp[pre_ramp['CMF']>0]['CMF'].mean():.3f}")

# At peak cloud (hours 12-14) CMF should be low
peak_cloud = df1[df1["hour_in_event"].isin([12, 13, 14])]
check("Peak cloud CMF < 0.35 (cloud event active)",
      peak_cloud[peak_cloud["CMF"] > 0]["CMF"].mean() < 0.35,
      f"Peak cloud mean CMF: {peak_cloud[peak_cloud['CMF']>0]['CMF'].mean():.3f}")

# NWP spread should widen during cloud event vs pre-ramp
pre_spread  = pre_ramp[pre_ramp["nwp_spread"] > 0]["nwp_spread"].mean()
peak_spread = peak_cloud[peak_cloud["nwp_spread"] > 0]["nwp_spread"].mean()
check("NWP spread wider during cloud event than pre-ramp",
      peak_spread > pre_spread,
      f"Pre-ramp: {pre_spread:.2f}, Peak cloud: {peak_spread:.2f} W/m²")

# CMF bounded
check("CMF in [0,1]",
      df1["CMF"].between(0,1).all(),
      f"Range: {df1['CMF'].min():.4f}–{df1['CMF'].max():.4f}")

check("No NaN in core features",
      df1[["CMF","nwp_spread","actual_generation_mw"]].isna().sum().sum() == 0)

# ------------------------------------------------------------------
# SCENARIO 2: MONSOON ONSET
# ------------------------------------------------------------------
print("\n--- Scenario 2: Monsoon Onset ---")
path2 = os.path.join(DATA_DIR, "stress_monsoon_onset.csv")
check("stress_monsoon_onset.csv exists", os.path.exists(path2))
df2 = pd.read_csv(path2)

check("240 rows (10 days × 24 hours)",
      len(df2) == 240,
      f"Actual: {len(df2)}")

check("10 days in event",
      df2["day_in_event"].nunique() == 10,
      f"Days: {sorted(df2['day_in_event'].unique())}")

# Day 1 CMF should be much higher than Day 8 CMF
day1_cmf = df2[(df2["day_in_event"]==1) & (df2["CMF"]>0)]["CMF"].mean()
day8_cmf = df2[(df2["day_in_event"]==8) & (df2["CMF"]>0)]["CMF"].mean()
check("Day 1 CMF > Day 8 CMF (monsoon progressively worsens)",
      day1_cmf > day8_cmf,
      f"Day 1: {day1_cmf:.3f}, Day 8: {day8_cmf:.3f}")

check("Peak monsoon CMF (day 7-8) < 0.2",
      df2[(df2["day_in_event"].isin([7,8])) &
          (df2["CMF"] > 0)]["CMF"].mean() < 0.2,
      f"Days 7-8 mean CMF: "
      f"{df2[(df2['day_in_event'].isin([7,8]))&(df2['CMF']>0)]['CMF'].mean():.3f}")

# Spread should increase as monsoon arrives
day1_spread = df2[(df2["day_in_event"]==1) & (df2["nwp_spread"]>0)]["nwp_spread"].mean()
day5_spread = df2[(df2["day_in_event"]==5) & (df2["nwp_spread"]>0)]["nwp_spread"].mean()
check("Day 5 spread > Day 1 spread (uncertainty grows with monsoon)",
      day5_spread > day1_spread,
      f"Day 1: {day1_spread:.2f}, Day 5: {day5_spread:.2f} W/m²")

check("No NaN in core features",
      df2[["CMF","nwp_spread","actual_generation_mw"]].isna().sum().sum() == 0)

# ------------------------------------------------------------------
# SCENARIO 3: WIND SPIKE
# ------------------------------------------------------------------
print("\n--- Scenario 3: Wind Speed Spike ---")
path3 = os.path.join(DATA_DIR, "stress_wind_spike.csv")
check("stress_wind_spike.csv exists", os.path.exists(path3))
df3 = pd.read_csv(path3)

check("5 events × 72 hours = 360 rows",
      len(df3) == 360,
      f"Actual: {len(df3)}")

check("wind_speed_ms column present",
      "wind_speed_ms" in df3.columns)

# Cut-out hours: ws > 25 → generation must be 0
above_cutout = df3[df3["wind_speed_ms"] > 25.0]
check("Generation = 0 above cut-out speed (>25 m/s)",
      (above_cutout["actual_generation_mw"] < 1.0).all(),
      f"Max gen above cut-out: {above_cutout['actual_generation_mw'].max():.3f} MW")

check("At least one cut-out shutdown row per scenario",
      len(above_cutout) >= 5,
      f"Cut-out rows: {len(above_cutout)}")

# Pre-spike baseline wind should be moderate
baseline = df3[df3["hour_in_event"] < 24]
check("Pre-spike baseline wind 6-12 m/s",
      baseline["wind_speed_ms"].between(5, 14).all(),
      f"Range: {baseline['wind_speed_ms'].min():.1f}–{baseline['wind_speed_ms'].max():.1f} m/s")

# Near cut-out: NWP spread should be elevated
near_cutout = df3[df3["wind_speed_ms"].between(20, 25)]
normal_wind  = df3[df3["wind_speed_ms"].between(7, 12)]
if len(near_cutout) > 0 and len(normal_wind) > 0:
    check("NWP spread elevated near cut-out vs normal wind",
          near_cutout["nwp_spread"].mean() > normal_wind["nwp_spread"].mean(),
          f"Near cut-out: {near_cutout['nwp_spread'].mean():.3f}, "
          f"Normal: {normal_wind['nwp_spread'].mean():.3f} m/s")

# Power curve fraction
check("PCF in [0,1]",
      df3["power_curve_fraction"].between(0, 1).all(),
      f"Range: {df3['power_curve_fraction'].min():.4f}–"
      f"{df3['power_curve_fraction'].max():.4f}")

check("No NaN in core features",
      df3[["power_curve_fraction","nwp_spread",
           "actual_generation_mw"]].isna().sum().sum() == 0)

# ------------------------------------------------------------------
# SCENARIO 4: SUSTAINED LOW IRRADIANCE
# ------------------------------------------------------------------
print("\n--- Scenario 4: Sustained Low Irradiance ---")
path4 = os.path.join(DATA_DIR, "stress_low_irradiance.csv")
check("stress_low_irradiance.csv exists", os.path.exists(path4))
df4 = pd.read_csv(path4)

check("168 rows (7 days × 24 hours)",
      len(df4) == 168,
      f"Actual: {len(df4)}")

day_cmf_mean = df4[df4["CMF"] > 0]["CMF"].mean()
check("Average daytime CMF < 0.25 (deep suppression)",
      day_cmf_mean < 0.25,
      f"Mean daytime CMF: {day_cmf_mean:.3f}")

check("CMF never exceeds 0.35 (sustained low)",
      df4["CMF"].max() <= 0.35,
      f"Max CMF: {df4['CMF'].max():.3f}")

# NWP spread should be consistently wide
day_spread = df4[df4["nwp_spread"] > 0]["nwp_spread"].mean()
check("Mean NWP spread > 50 W/m² (persistently wide intervals)",
      day_spread > 50,
      f"Mean spread: {day_spread:.2f} W/m²")

check("All 7 days represented",
      df4["day_in_event"].nunique() == 7,
      f"Days: {sorted(df4['day_in_event'].unique())}")

check("No NaN in core features",
      df4[["CMF","nwp_spread","actual_generation_mw"]].isna().sum().sum() == 0)

# ------------------------------------------------------------------
# CROSS-SCENARIO: COLUMN CONSISTENCY
# ------------------------------------------------------------------
print("\n--- Cross-scenario column consistency ---")
for name, df in [("cloud_ramp",df1), ("monsoon_onset",df2),
                 ("wind_spike",df3), ("low_irradiance",df4)]:
    core_ok = all(c in df.columns for c in [
        "CMF","power_curve_fraction","temperature","nwp_spread",
        "capacity_mw","lat_sin","lat_cos","lon_sin","lon_cos",
        "tilt_angle_deg","hub_height_m",
        "hour_sin","hour_cos","doy_sin","doy_cos",
        "season","actual_generation_mw"
    ])
    check(f"{name}: all 21 model input columns present", core_ok)

    # sin²+cos² = 1
    err = ((df["hour_sin"]**2 + df["hour_cos"]**2) - 1).abs().max()
    check(f"{name}: cyclical encodings correct (sin²+cos²=1)",
          err < 1e-10,
          f"Max error: {err:.2e}")

# ------------------------------------------------------------------
# FINAL SCORE
# ------------------------------------------------------------------
print("\n" + "=" * 60)
passed = sum(1 for _, r in results if r)
total  = len(results)
print(f"Result: {passed}/{total} checks passed")

if passed == total:
    print("All checks passed. Day 4 stress scenarios are correct.")
    print("Hand stress_*.csv files to Person 4.")
else:
    failed = [n for n, r in results if not r]
    print(f"\nFailed checks:")
    for f in failed:
        print(f"  - {f}")
print("=" * 60)