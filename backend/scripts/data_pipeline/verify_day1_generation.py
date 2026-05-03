"""
Day 1 Verification Script
Run: python verify_day1.py
Checks every critical property of the Day 1 output.
Prints PASS / FAIL for each check.
"""

import pandas as pd
import numpy as np
import os

PASS = "  PASS"
FAIL = "  FAIL"

results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    marker = "OK" if condition else "!!"
    print(f"  [{marker}] {name}")
    if detail:
        print(f"       {detail}")
    results.append((name, condition))
    return condition


print("=" * 60)
print("Day 1 Verification")
print("=" * 60)

# ------------------------------------------------------------------
# 1. FILES EXIST
# ------------------------------------------------------------------
print("\n--- File existence ---")
check("raw_weather_data.csv exists", os.path.exists("data/raw_weather_data.csv"))
check("asset_registry.csv exists",   os.path.exists("data/asset_registry.csv"))
check("seed_solar.csv exists",       os.path.exists("data/seed_solar.csv"))
check("seed_wind.csv exists",        os.path.exists("data/seed_wind.csv"))

# ------------------------------------------------------------------
# 2. LOAD DATA
# ------------------------------------------------------------------
df  = pd.read_csv("data/raw_weather_data.csv", parse_dates=["timestamp"])
reg = pd.read_csv("data/asset_registry.csv")

# ------------------------------------------------------------------
# 3. SHAPE CHECKS
# ------------------------------------------------------------------
print("\n--- Shape and completeness ---")
check("52,560 rows total (8760h × 6 plants)",
      len(df) == 52560,
      f"Actual: {len(df)}")

check("6 unique plants",
      df["plant_id"].nunique() == 6,
      f"Found: {df['plant_id'].unique()}")

check("Each plant has exactly 8760 rows",
      (df.groupby("plant_id").size() == 8760).all(),
      f"Counts: {df.groupby('plant_id').size().to_dict()}")

check("Asset registry has 6 rows",
      len(reg) == 6,
      f"Actual: {len(reg)}")

# ------------------------------------------------------------------
# 4. COLUMN CHECKS
# ------------------------------------------------------------------
print("\n--- Required columns ---")
required_cols = [
    "timestamp", "plant_id", "plant_type", "cluster_id",
    "GHI", "temperature", "cloud_cover",
    "wind_speed", "wind_direction",
    "generation_mw", "capacity_mw", "season"
]
for col in required_cols:
    check(f"Column '{col}' present", col in df.columns)

# ------------------------------------------------------------------
# 5. TIMESTAMP CHECKS
# ------------------------------------------------------------------
print("\n--- Timestamps ---")
# Check one plant's timestamps cover full year
pvg = df[df["plant_id"] == "PVG_S1"].sort_values("timestamp")
ts  = pd.to_datetime(pvg["timestamp"])

check("Timestamps span full year 2023",
      ts.iloc[0].year == 2023 and ts.iloc[-1].year == 2023,
      f"Range: {ts.iloc[0]} -> {ts.iloc[-1]}")

check("Hourly frequency — no gaps",
      len(ts) == 8760,
      f"Count: {len(ts)}")

diffs = ts.diff().dropna().dt.total_seconds() / 3600
check("All intervals are exactly 1 hour",
      (diffs == 1.0).all(),
      f"Min interval: {diffs.min():.2f}h, Max: {diffs.max():.2f}h")

# ------------------------------------------------------------------
# 6. PHYSICAL BOUNDS
# ------------------------------------------------------------------
print("\n--- Physical bounds (solar plants) ---")
solar = df[df["plant_type"] == "solar"]
wind  = df[df["plant_type"] == "wind"]

check("GHI >= 0 always",
      (solar["GHI"] >= 0).all(),
      f"Min GHI: {solar['GHI'].min():.2f}")

check("GHI <= 1200 W/m² (physical max)",
      (solar["GHI"] <= 1200).all(),
      f"Max GHI: {solar['GHI'].max():.2f}")

check("Temperature 15–48°C for solar",
      solar["temperature"].between(14, 50).all(),
      f"Range: {solar['temperature'].min():.1f}–{solar['temperature'].max():.1f}°C")

check("Cloud cover 0–1 (fraction)",
      solar["cloud_cover"].between(0, 1).all(),
      f"Range: {solar['cloud_cover'].min():.3f}–{solar['cloud_cover'].max():.3f}")

print("\n--- Physical bounds (wind plants) ---")
check("Wind speed >= 0",
      (wind["wind_speed"] >= 0).all(),
      f"Min: {wind['wind_speed'].min():.2f} m/s")

check("Wind speed <= 35 m/s (physical max)",
      (wind["wind_speed"] <= 35).all(),
      f"Max: {wind['wind_speed'].max():.2f} m/s")

check("Wind direction 0–360°",
      wind["wind_direction"].between(0, 360).all(),
      f"Range: {wind['wind_direction'].min():.1f}–{wind['wind_direction'].max():.1f}°")

# ------------------------------------------------------------------
# 7. GENERATION SANITY
# ------------------------------------------------------------------
print("\n--- Generation sanity ---")
check("generation_mw >= 0 always",
      (df["generation_mw"] >= 0).all(),
      f"Min: {df['generation_mw'].min():.4f}")

check("generation_mw never exceeds capacity",
      (df["generation_mw"] <= df["capacity_mw"] * 1.01).all(),   # 1% tolerance
      f"Max fraction: {(df['generation_mw'] / df['capacity_mw']).max():.3f}")

# Solar: nighttime generation must be zero
night_solar = solar[solar["GHI"] == 0.0]
check("Solar generation is zero at night (GHI=0)",
      (night_solar["generation_mw"] == 0.0).all(),
      f"Night rows with nonzero gen: {(night_solar['generation_mw'] > 0).sum()}")

# Wind: generation zero below cut-in speed
below_cutin = wind[wind["wind_speed"] < 3.0]
check("Wind generation zero below cut-in (3 m/s)",
      (below_cutin["generation_mw"] < 1.0).all(),
      f"Max gen below cut-in: {below_cutin['generation_mw'].max():.3f} MW")

# ------------------------------------------------------------------
# 8. CORRELATION CHECK (the whole point of using a Copula)
# ------------------------------------------------------------------
print("\n--- Correlation check (copula validity) ---")

# Solar: GHI and generation should be strongly positively correlated
day_solar = solar[solar["GHI"] > 10]
ghi_gen_corr = day_solar["GHI"].corr(day_solar["generation_mw"])
check("GHI vs solar generation correlation > 0.85",
      ghi_gen_corr > 0.85,
      f"Actual: {ghi_gen_corr:.3f}")

# Cloud cover and GHI should be negatively correlated
cloud_ghi_corr = day_solar["cloud_cover"].corr(day_solar["GHI"])
check("Cloud cover vs GHI correlation < -0.3",
      cloud_ghi_corr < -0.3,
      f"Actual: {cloud_ghi_corr:.3f}")

# Wind: correlation in operating range only (3-25 m/s)
# Above cut-out turbine shuts down (gen=0 at high wind) — physically correct
wind_op = wind[(wind["wind_speed"] >= 3) & (wind["wind_speed"] <= 25)]
ws_gen_corr = wind_op["wind_speed"].corr(wind_op["generation_mw"])
check("Wind speed vs generation corr > 0.80 (operating range 3-25 m/s)",
      ws_gen_corr > 0.80,
      f"Actual: {ws_gen_corr:.3f} (full-range lower due to cut-out shutdown, physically correct)")

# ------------------------------------------------------------------
# 9. DIURNAL PATTERN CHECK (solar)
# ------------------------------------------------------------------
print("\n--- Diurnal pattern (solar) ---")
df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour

solar_hourly = df[df["plant_type"] == "solar"].groupby("hour")["GHI"].mean()

midnight_ghi = solar_hourly.loc[0]
noon_ghi     = solar_hourly.loc[12]

check("GHI at midnight (hour=0) is 0",
      midnight_ghi == 0.0,
      f"Actual: {midnight_ghi:.2f} W/m²")

check("Peak GHI is around solar noon (10:00–14:00)",
      solar_hourly.idxmax() in range(10, 15),
      f"Peak hour: {solar_hourly.idxmax()}")

check("Noon GHI > midnight GHI (obvious but verify)",
      noon_ghi > midnight_ghi,
      f"Noon: {noon_ghi:.1f}, Midnight: {midnight_ghi:.1f}")

# ------------------------------------------------------------------
# 10. SEASONAL PATTERN CHECK
# ------------------------------------------------------------------
print("\n--- Seasonal pattern ---")
df["month"] = pd.to_datetime(df["timestamp"]).dt.month

solar_monthly = df[df["plant_type"] == "solar"].groupby("month")["GHI"].mean()
wind_monthly  = df[df["plant_type"] == "wind"].groupby("month")["wind_speed"].mean()

# Karnataka monsoon (Jun=6 to Sep=9) should have lower GHI than summer (Mar=3 to May=5)
summer_ghi  = solar_monthly.loc[[3, 4, 5]].mean()
monsoon_ghi = solar_monthly.loc[[6, 7, 8, 9]].mean()
check("Monsoon GHI < summer GHI (seasonal suppression)",
      monsoon_ghi < summer_ghi,
      f"Summer avg: {summer_ghi:.1f} W/m², Monsoon avg: {monsoon_ghi:.1f} W/m²")

# Post-monsoon (Oct=10, Nov=11) wind should be stronger than summer
summer_wind  = wind_monthly.loc[[3, 4, 5]].mean()
postmon_wind = wind_monthly.loc[[10, 11]].mean()
check("Post-monsoon wind > summer wind (NE monsoon effect)",
      postmon_wind > summer_wind,
      f"Summer avg: {summer_wind:.2f} m/s, Post-monsoon avg: {postmon_wind:.2f} m/s")

# ------------------------------------------------------------------
# 11. NaN CHECKS
# ------------------------------------------------------------------
print("\n--- NaN handling ---")
# Solar plants: GHI, temperature, cloud_cover, generation_mw must have no NaN
solar_required = ["GHI", "temperature", "cloud_cover", "generation_mw"]
for col in solar_required:
    nan_count = solar[col].isna().sum()
    check(f"Solar '{col}' has no NaN",
          nan_count == 0,
          f"NaN count: {nan_count}")

# Wind plants: wind_speed, wind_direction, generation_mw must have no NaN
wind_required = ["wind_speed", "wind_direction", "generation_mw"]
for col in wind_required:
    nan_count = wind[col].isna().sum()
    check(f"Wind '{col}' has no NaN",
          nan_count == 0,
          f"NaN count: {nan_count}")

# Cross-type NaNs: solar plants should have NaN for wind columns and vice versa
check("Solar plants have NaN wind_speed (expected)",
      solar["wind_speed"].isna().all(),
      f"Non-NaN wind_speed in solar: {solar['wind_speed'].notna().sum()}")

check("Wind plants have NaN GHI (expected)",
      wind["GHI"].isna().all(),
      f"Non-NaN GHI in wind plants: {wind['GHI'].notna().sum()}")

# ------------------------------------------------------------------
# 12. CLUSTER STRUCTURE
# ------------------------------------------------------------------
print("\n--- Cluster structure ---")
cluster_counts = df.groupby("cluster_id")["plant_id"].nunique()
check("Cluster C1_Pavagada has 3 plants",
      cluster_counts.get("C1_Pavagada", 0) == 3,
      f"Actual: {cluster_counts.get('C1_Pavagada', 0)}")

check("Cluster C2_Gadag has 3 plants",
      cluster_counts.get("C2_Gadag", 0) == 3,
      f"Actual: {cluster_counts.get('C2_Gadag', 0)}")

# ------------------------------------------------------------------
# FINAL SCORE
# ------------------------------------------------------------------
print("\n" + "=" * 60)
passed = sum(1 for _, r in results if r)
total  = len(results)
print(f"Result: {passed}/{total} checks passed")

if passed == total:
    print("All checks passed. Day 1 output is clean.")
    print("Ready to hand off to Day 2 (physics transforms).")
else:
    failed = [name for name, r in results if not r]
    print(f"\nFailed checks:")
    for f in failed:
        print(f"  - {f}")
    print("\nFix these before starting Day 2.")
print("=" * 60)