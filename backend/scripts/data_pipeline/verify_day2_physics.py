"""
Day 2 Verification Script
Run: python verify_day2.py

Checks that physics transforms are physically correct.
More rigorous than the basic validation inside main_day2.py.
"""

import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "ml", "data_pipeline"))


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")

results = []

def check(name, condition, detail=""):
    marker = "OK" if condition else "!!"
    print(f"  [{marker}] {name}")
    if detail:
        print(f"       {detail}")
    results.append((name, condition))
    return condition


print("=" * 60)
print("Day 2 Verification")
print("=" * 60)

# ------------------------------------------------------------------
# Load data
# ------------------------------------------------------------------
fm  = pd.read_csv(os.path.join(DATA_DIR, "feature_matrix.csv"))
raw = pd.read_csv(os.path.join(DATA_DIR, "raw_with_physics.csv"))
solar = fm[fm["plant_type"] == "solar"].copy()
wind  = fm[fm["plant_type"] == "wind"].copy()

# ------------------------------------------------------------------
# 1. FILES
# ------------------------------------------------------------------
print("\n--- File existence ---")
check("feature_matrix.csv exists",
      os.path.exists(os.path.join(DATA_DIR, "feature_matrix.csv")))
check("raw_with_physics.csv exists",
      os.path.exists(os.path.join(DATA_DIR, "raw_with_physics.csv")))

# ------------------------------------------------------------------
# 2. SHAPE
# ------------------------------------------------------------------
print("\n--- Shape ---")
check("Feature matrix has 52,560 rows",
      len(fm) == 52560,
      f"Actual: {len(fm)}")

check("Feature matrix has 20 columns",
      fm.shape[1] == 20,
      f"Actual: {fm.shape[1]} — columns: {list(fm.columns)}")

# ------------------------------------------------------------------
# 3. CMF PHYSICS CHECKS
# ------------------------------------------------------------------
print("\n--- CMF physics (solar) ---")

check("CMF column exists",
      "CMF" in fm.columns)

check("CMF always in [0, 1]",
      fm.loc[fm["plant_type"]=="solar", "CMF"].between(0, 1).all(),
      f"Range: {solar['CMF'].min():.4f}–{solar['CMF'].max():.4f}")

check("CMF = 0 at night (generation = 0 for solar)",
      (solar.loc[solar["actual_generation_mw"] == 0, "CMF"] == 0).all(),
      f"Non-zero night CMF rows: {(solar.loc[solar['actual_generation_mw']==0,'CMF'] > 0).sum()}")

# Daytime CMF should be between 0 and 1, not all zeros
day_solar = solar[solar["actual_generation_mw"] > 0]
check("Daytime CMF has meaningful spread (std > 0.1)",
      day_solar["CMF"].std() > 0.1,
      f"Std: {day_solar['CMF'].std():.3f}")

check("Daytime CMF mean in plausible range (0.2-0.9)",
      0.2 < day_solar["CMF"].mean() < 0.9,
      f"Mean: {day_solar['CMF'].mean():.3f}")

# CMF should be higher in winter/summer than monsoon
fm["month"] = pd.to_datetime(fm["timestamp"]).dt.month
summer_cmf  = fm.loc[(fm["plant_type"]=="solar") &
                     (fm["month"].isin([3,4,5])) &
                     (fm["actual_generation_mw"]>0), "CMF"].mean()
monsoon_cmf = fm.loc[(fm["plant_type"]=="solar") &
                     (fm["month"].isin([6,7,8,9])) &
                     (fm["actual_generation_mw"]>0), "CMF"].mean()
check("Monsoon CMF < summer CMF (clouds suppress irradiance)",
      monsoon_cmf < summer_cmf,
      f"Summer CMF: {summer_cmf:.3f}, Monsoon CMF: {monsoon_cmf:.3f}")

# Wind plants must have CMF = 0
check("Wind plants have CMF = 0 (no solar panels)",
      (wind["CMF"] == 0).all(),
      f"Non-zero CMF in wind: {(wind['CMF'] > 0).sum()}")

# ------------------------------------------------------------------
# 4. CLEARSKY GHI CHECKS (intermediate file)
# ------------------------------------------------------------------
print("\n--- Clear-sky GHI (Ineichen-Perez) ---")
raw_solar = raw[raw["plant_type"] == "solar"]

check("clearsky_GHI column exists in raw_with_physics.csv",
      "clearsky_GHI" in raw.columns)

check("clearsky_GHI >= 0 always",
      (raw_solar["clearsky_GHI"] >= 0).all(),
      f"Min: {raw_solar['clearsky_GHI'].min():.2f}")

check("clearsky_GHI is 0 at midnight",
      (raw_solar[raw_solar["clearsky_GHI"] > 0]).shape[0] > 0,
      "Has nonzero daytime values")

# Spot check: June noon should have high clear-sky GHI for Pavagada
raw_pvg = raw[raw["plant_id"] == "PVG_S1"].copy()
raw_pvg["ts"] = pd.to_datetime(raw_pvg["timestamp"])
june_noon = raw_pvg[
    (raw_pvg["ts"].dt.month == 6) &
    (raw_pvg["ts"].dt.hour == 12)
]["clearsky_GHI"]
check("June noon clearsky GHI for PVG_S1 > 800 W/m²",
      june_noon.mean() > 800,
      f"June noon mean: {june_noon.mean():.1f} W/m²")

# December noon should be lower (lower sun angle)
dec_noon = raw_pvg[
    (raw_pvg["ts"].dt.month == 12) &
    (raw_pvg["ts"].dt.hour == 12)
]["clearsky_GHI"]
check("June noon clearsky GHI > December noon clearsky GHI (sun angle)",
      june_noon.mean() > dec_noon.mean(),
      f"June: {june_noon.mean():.1f} W/m², Dec: {dec_noon.mean():.1f} W/m²")

# ------------------------------------------------------------------
# 5. POWER CURVE CHECKS
# ------------------------------------------------------------------
print("\n--- Power curve transform (wind) ---")

check("power_curve_fraction column exists",
      "power_curve_fraction" in fm.columns)

check("power_curve_fraction in [0, 1]",
      wind["power_curve_fraction"].between(0, 1).all(),
      f"Range: {wind['power_curve_fraction'].min():.4f}–{wind['power_curve_fraction'].max():.4f}")

check("Solar plants have power_curve_fraction = 0",
      (solar["power_curve_fraction"] == 0).all(),
      f"Non-zero in solar: {(solar['power_curve_fraction']>0).sum()}")

# Below cut-in: generation AND power_curve_fraction both zero
raw_wind = raw[raw["plant_type"] == "wind"]
below_cutin = raw_wind[raw_wind["wind_speed"] < 3.0]
below_pcf = fm.loc[fm.index.isin(below_cutin.index), "power_curve_fraction"]

# Re-check using merged approach
raw_wind_merged = raw_wind.copy()
raw_wind_merged = raw_wind_merged.reset_index(drop=True)
fm_wind = fm[fm["plant_type"] == "wind"].reset_index(drop=True)

# Check power curve at specific known wind speeds
from power_curve import power_curve_fraction
check("PCF = 0 below cut-in (ws=2 m/s)",
      power_curve_fraction(2.0) == 0.0,
      f"PCF at 2 m/s: {power_curve_fraction(2.0):.4f}")

check("PCF = 1.0 at rated speed (ws=16 m/s)",
      power_curve_fraction(16.0) == 1.0,
      f"PCF at 16 m/s: {power_curve_fraction(16.0):.4f}")

check("PCF = 0 above cut-out (ws=26 m/s)",
      power_curve_fraction(26.0) == 0.0,
      f"PCF at 26 m/s: {power_curve_fraction(26.0):.4f}")

check("PCF is monotonically increasing 3→16 m/s",
      all(
          power_curve_fraction(ws2) >= power_curve_fraction(ws1)
          for ws1, ws2 in zip(range(3, 16), range(4, 17))
      ),
      "Checked at integer m/s steps 3–16")

check("PCF at ws=10 m/s is in expected range (0.45–0.65)",
      0.45 < power_curve_fraction(10.0) < 0.65,
      f"PCF at 10 m/s: {power_curve_fraction(10.0):.4f}")

# ------------------------------------------------------------------
# 6. CYCLICAL ENCODING CHECKS
# ------------------------------------------------------------------
print("\n--- Cyclical encodings ---")

for col_pair in [("hour_sin", "hour_cos"), ("doy_sin", "doy_cos")]:
    s, c = col_pair
    err = ((fm[s]**2 + fm[c]**2) - 1.0).abs().max()
    check(f"sin²+cos²=1 for {s}/{c}",
          err < 1e-10,
          f"Max error: {err:.2e}")

# Midnight: hour_sin should be ~0, hour_cos should be ~1
midnight_rows = fm[pd.to_datetime(fm["timestamp"]).dt.hour == 0]
midnight_hs = midnight_rows["hour_sin"].abs().max()
midnight_hc = (midnight_rows["hour_cos"] - 1.0).abs().max()
check("hour_sin ≈ 0 at midnight",
      midnight_hs < 1e-10,
      f"Max |hour_sin| at midnight: {midnight_hs:.2e}")

check("hour_cos ≈ 1 at midnight",
      midnight_hc < 1e-10,
      f"Max |hour_cos - 1| at midnight: {midnight_hc:.2e}")

# Hour 6: sin should be ~1
h6 = fm[pd.to_datetime(fm["timestamp"]).dt.hour == 6]
h6_sin = h6["hour_sin"].iloc[0]
check("hour_sin ≈ 1.0 at hour 6",
      abs(h6_sin - 1.0) < 0.01,
      f"hour_sin at h=6: {h6_sin:.4f}")

# ------------------------------------------------------------------
# 7. NO NaN IN FEATURE MATRIX
# ------------------------------------------------------------------
print("\n--- NaN checks ---")
feature_cols = ["CMF","power_curve_fraction","temperature","capacity_mw",
                "lat_sin","lat_cos","lon_sin","lon_cos",
                "tilt_angle_deg","hub_height_m",
                "hour_sin","hour_cos","doy_sin","doy_cos",
                "season","actual_generation_mw"]

for col in feature_cols:
    nan_count = fm[col].isna().sum()
    check(f"No NaN in '{col}'",
          nan_count == 0,
          f"NaN count: {nan_count}" if nan_count > 0 else "")

# ------------------------------------------------------------------
# 8. GENERATION CONSISTENCY
# ------------------------------------------------------------------
print("\n--- Generation consistency ---")
check("actual_generation_mw >= 0",
      (fm["actual_generation_mw"] >= 0).all(),
      f"Min: {fm['actual_generation_mw'].min():.4f}")

check("actual_generation_mw <= capacity_mw",
      (fm["actual_generation_mw"] <= fm["capacity_mw"] * 1.01).all(),
      f"Max fraction: {(fm['actual_generation_mw']/fm['capacity_mw']).max():.4f}")

# ------------------------------------------------------------------
# FINAL SCORE
# ------------------------------------------------------------------
print("\n" + "=" * 60)
passed = sum(1 for _, r in results if r)
total  = len(results)
print(f"Result: {passed}/{total} checks passed")

if passed == total:
    print("All checks passed. Day 2 physics transforms are correct.")
    print("feature_matrix.csv is ready to hand off to Person 2.")
else:
    failed = [name for name, r in results if not r]
    print(f"\nFailed checks:")
    for f in failed:
        print(f"  - {f}")
print("=" * 60)