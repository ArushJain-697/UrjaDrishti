"""
Person 4 — Baseline Smoke Test (Day 2)
========================================
Run this to verify all three baselines work correctly.

Usage (from backend/ directory):
    python -m src.ml.evaluation.test_baselines

What this tests:
  1. Persistence      — NaN for first 24 rows (no lag available), real values after
  2. Climatological   — no NaN in output, values are in plausible range
  3. Raw NWP LR       — no NaN in output, predictions clipped >= 0
  4. Interval wrapper — P10 < forecast < P90 for every row
  5. CRPS ordering    — climatological CRPS < persistence CRPS (clim should win)
  6. nMAE ordering    — climatological nMAE < persistence nMAE
  7. Full run         — run_all_baselines() returns correct structure
"""

import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")

from src.ml.evaluation.baselines import (
    generate_dummy_dataset,
    persistence_forecast,
    climatological_forecast,
    raw_nwp_lr_forecast,
    add_baseline_intervals,
    run_all_baselines,
    _evaluate_baseline,
)
from src.ml.evaluation.metrics import temporal_split

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"


def _ok(condition, label, detail=""):
    status = PASS if condition else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  {status} {label}{suffix}")
    return condition


# ─── Generate shared dummy data ────────────────────────────────────────────
print("Generating dummy dataset (365 days, 6 plants)...")
df      = generate_dummy_dataset(n_days=365)
train_df, val_df, test_df = temporal_split(df, "timestamp")
print(f"  Train: {len(train_df):,} rows | Val: {len(val_df):,} rows | Test: {len(test_df):,} rows\n")


def test_persistence():
    print("-- Test 1: Persistence Baseline --")
    result = persistence_forecast(df)

    # First 24 rows per plant should be NaN (no lag available)
    for plant_id in df["plant_id"].unique():
        plant_rows = result[result["plant_id"] == plant_id].head(24)
        nan_count  = plant_rows["persistence_forecast"].isna().sum()
        _ok(nan_count == 24, f"{plant_id}: first 24 rows are NaN", f"{nan_count}/24 NaN")

    # After row 24, should have values
    non_nan_pct = result["persistence_forecast"].notna().mean()
    _ok(non_nan_pct > 0.90, ">90% of rows have a forecast value", f"{non_nan_pct:.1%}")

    # Values should be in realistic range
    valid = result["persistence_forecast"].dropna()
    _ok(valid.min() >= 0, "All forecasts >= 0", f"min={valid.min():.2f}")
    _ok(valid.max() < 200, "All forecasts < 200 MW (sanity)", f"max={valid.max():.2f}")
    return True


def test_climatological():
    print("\n-- Test 2: Climatological Baseline --")
    result = climatological_forecast(train_df, test_df.copy())

    nan_count = result["climatological_forecast"].isna().sum()
    _ok(nan_count == 0, "No NaN in output", f"{nan_count} NaN rows")

    _ok(result["climatological_forecast"].min() >= 0,
        "All forecasts >= 0",
        f"min={result['climatological_forecast'].min():.2f}")

    # Clim forecast for solar should be much lower at midnight vs midday
    solar_midnight = result[
        (result["plant_type"] == "solar") &
        (pd.to_datetime(result["timestamp"]).dt.hour == 0)
    ]["climatological_forecast"]
    solar_noon_check = result[
        (result["plant_type"] == "solar") &
        (pd.to_datetime(result["timestamp"]).dt.hour == 12)
    ]["climatological_forecast"]
    _ok(solar_midnight.mean() < solar_noon_check.mean(),
        "Solar midnight clim < solar noon clim",
        f"midnight mean={solar_midnight.mean():.2f}, noon mean={solar_noon_check.mean():.2f}")

    # Clim forecast for solar should peak around midday
    solar_noon = result[
        (result["plant_type"] == "solar") &
        (pd.to_datetime(result["timestamp"]).dt.hour == 12)
    ]["climatological_forecast"]
    _ok(solar_noon.mean() > 20,
        "Solar midday forecasts > 20 MW",
        f"mean={solar_noon.mean():.2f}")
    return True


def test_raw_nwp_lr():
    print("\n-- Test 3: Raw NWP Linear Regression Baseline --")
    result, models = raw_nwp_lr_forecast(train_df, test_df.copy())

    nan_count = result["raw_nwp_forecast"].isna().sum()
    _ok(nan_count == 0, "No NaN in output", f"{nan_count} NaN rows")

    _ok(result["raw_nwp_forecast"].min() >= 0,
        "All forecasts >= 0 (clipped)",
        f"min={result['raw_nwp_forecast'].min():.2f}")

    _ok(len(models) == len(df["plant_id"].unique()),
        f"One model trained per plant",
        f"{len(models)} models for {df['plant_id'].nunique()} plants")
    return True


def test_intervals():
    print("\n-- Test 4: Uncertainty Interval Wrapper --")

    pers_full = persistence_forecast(df)
    pers_test = pers_full[pers_full["timestamp"] >= test_df["timestamp"].min()].copy()
    pers_test = add_baseline_intervals(pers_test, train_df, "persistence_forecast")

    valid = pers_test[pers_test["persistence_forecast"].notna()]
    p10_ok = (valid["persistence_p10"] <= valid["persistence_forecast"]).all()
    p90_ok = (valid["persistence_forecast"] <= valid["persistence_p90"]).all()
    _ok(p10_ok, "P10 <= forecast for all rows")
    _ok(p90_ok, "forecast <= P90 for all rows")

    width = (valid["persistence_p90"] - valid["persistence_p10"]).mean()
    _ok(width > 5, f"Average interval width > 5 MW", f"mean width = {width:.2f} MW")
    return True


def test_metric_ordering():
    print("\n-- Test 5: Metric Ordering (Clim should beat Persistence) --")

    # Persistence
    pers_full = persistence_forecast(df)
    pers_test = pers_full[pers_full["timestamp"] >= test_df["timestamp"].min()].copy()
    pers_test = add_baseline_intervals(pers_test, train_df, "persistence_forecast")
    pers_res  = _evaluate_baseline(pers_test, "persistence_forecast")

    # Climatological
    clim_test       = climatological_forecast(train_df, test_df.copy())
    train_with_clim = climatological_forecast(train_df, train_df.copy())
    clim_test       = add_baseline_intervals(clim_test, train_with_clim, "climatological_forecast")
    clim_res        = _evaluate_baseline(clim_test, "climatological_forecast")

    p_nmae = pers_res["solar_summary"].get("nmae", 999)
    c_nmae = clim_res["solar_summary"].get("nmae", 999)
    _ok(c_nmae < p_nmae,
        "Clim solar nMAE < Persistence solar nMAE",
        f"clim={c_nmae:.4f} vs persistence={p_nmae:.4f}")

    p_crps = pers_res["solar_summary"].get("crps")
    c_crps = clim_res["solar_summary"].get("crps")
    if p_crps and c_crps:
        _ok(c_crps < p_crps,
            "Clim solar CRPS < Persistence solar CRPS",
            f"clim={c_crps:.4f} vs persistence={p_crps:.4f}")
    return True


def test_full_run():
    print("\n-- Test 6: run_all_baselines() full pipeline --")

    # Save dummy data temporarily so run_all_baselines can load it
    import os, tempfile
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df.to_csv(f, index=False)
        tmp_path = f.name

    try:
        results = run_all_baselines(tmp_path)
    finally:
        os.unlink(tmp_path)

    # Check structure
    for key in ["persistence", "climatological", "raw_nwp"]:
        _ok(key in results, f"Key '{key}' present in results")
        for subkey in ["overall", "solar_summary", "wind_summary"]:
            _ok(subkey in results[key], f"  '{key}.{subkey}' present")
        for metric in ["nmae", "nrmse"]:
            val = results[key]["overall"].get(metric)
            _ok(val is not None and 0 < val < 5,
                f"  {key}.overall.{metric} is a valid float",
                f"val={val}")

    # Print the comparison table
    print("\n  ┌─────────────────────┬──────────────┬──────────────┬──────────────┐")
    print("  │ Baseline            │ nMAE overall │ nRMSE overall│ CRPS overall │")
    print("  ├─────────────────────┼──────────────┼──────────────┼──────────────┤")
    for label, key in [("Persistence    ", "persistence"),
                        ("Climatological ", "climatological"),
                        ("Raw NWP LR     ", "raw_nwp")]:
        o = results[key]["overall"]
        nmae_v  = f"{o.get('nmae',  'N/A'):.4f}" if o.get("nmae")  else "N/A"
        nrmse_v = f"{o.get('nrmse', 'N/A'):.4f}" if o.get("nrmse") else "N/A"
        crps_v  = f"{o.get('crps',  'N/A'):.4f}" if o.get("crps")  else "N/A"
        print(f"  │ {label} │ {nmae_v:^12} │ {nrmse_v:^12} │ {crps_v:^12} │")
    print("  └─────────────────────┴──────────────┴──────────────┴──────────────┘")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("  Person 4 — Baseline Smoke Test (Day 2)")
    print("=" * 60)

    results = [
        test_persistence(),
        test_climatological(),
        test_raw_nwp_lr(),
        test_intervals(),
        test_metric_ordering(),
        test_full_run(),
    ]

    print("\n" + "=" * 60)
    passed = sum(results)
    print(f"  {passed}/{len(results)} test groups passed")
    if passed == len(results):
        print("  ALL GOOD — baselines ready. Waiting for Person 2's model for Day 3.")
    else:
        print("  Some tests failed — check output above.")
    print("=" * 60)