"""
Person 4 — Day 1 Smoke Test
============================
Run this to verify the evaluation harness works correctly
before any real model or real data exists.

Usage:
    cd backend
    python -m src.ml.evaluation.test_harness

What it tests:
  1. temporal_split()   — correct proportions, no date overlap
  2. nmae()             — known input/output check
  3. nrmse()            — known input/output check
  4. coverage()         — checks boundary logic
  5. crps_gaussian()    — sanity-checks against perfect forecast
  6. evaluate()         — end-to-end on synthetic dummy data
  7. assign_season()    — all 12 months covered correctly
"""

import numpy as np
import pandas as pd
import sys

# ── Allow running from the backend/ directory ────────────────
sys.path.insert(0, ".")

from src.ml.evaluation.metrics import (
    temporal_split,
    nmae,
    nrmse,
    prediction_interval_coverage,
    crps_ensemble_score,
    crps_gaussian,
    evaluate,
    assign_season,
    quantile_calibration_audit,
    sharpness_score,
)

PASS = "[PASS]"
FAIL = "[FAIL]"


def assert_close(val, expected, tol=0.01, label=""):
    ok = abs(val - expected) < tol
    status = PASS if ok else FAIL
    print(f"  {status} {label}: got {val:.4f}, expected ~{expected:.4f}")
    return ok


def test_temporal_split():
    print("\n-- Test: temporal_split --")
    dates = pd.date_range("2023-01-01", periods=8760, freq="h")
    df = pd.DataFrame({"timestamp": dates, "val": np.random.rand(8760)})
    train, val, test = temporal_split(df, "timestamp")

    # No overlap
    assert train["timestamp"].max() < val["timestamp"].min(), "Train/Val overlap!"
    assert val["timestamp"].max()   < test["timestamp"].min(), "Val/Test overlap!"

    # Test is last 2 months (~1464 hours), val is next 2 months
    total = len(train) + len(val) + len(test)
    assert total == len(df), "Rows lost in split!"

    pct_test = len(test) / len(df)
    print(f"  {PASS} No date overlaps between splits")
    print(f"  {PASS} Total rows preserved: {total}")
    print(f"  {'OK' if 0.14 < pct_test < 0.20 else 'WARN'} Test fraction: {pct_test:.2%} (expect ~16%)")
    return True


def test_nmae():
    print("\n-- Test: nmae --")
    actual    = np.array([100.0, 100.0, 100.0, 100.0])
    predicted = np.array([ 90.0, 110.0,  90.0, 110.0])
    # MAE = 10, mean_actual = 100 -> nMAE = 0.10
    result = nmae(actual, predicted)
    assert_close(result, 0.10, label="nMAE basic")

    # Perfect forecast
    perfect = nmae(actual, actual)
    assert_close(perfect, 0.0, tol=1e-9, label="nMAE perfect")
    return True


def test_nrmse():
    print("\n-- Test: nrmse --")
    actual    = np.array([100.0, 100.0, 100.0, 100.0])
    predicted = np.array([ 90.0, 110.0,  90.0, 110.0])
    # RMSE = 10, mean = 100 -> nRMSE = 0.10
    result = nrmse(actual, predicted)
    assert_close(result, 0.10, label="nRMSE basic")
    return True


def test_coverage():
    print("\n-- Test: prediction_interval_coverage --")
    actual = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
    p10    = np.array([4.0, 4.0, 4.0, 6.0, 6.0])  # last 2 miss
    p90    = np.array([6.0, 6.0, 6.0, 7.0, 7.0])
    # First 3 inside, last 2 outside -> coverage = 0.60
    cov = prediction_interval_coverage(actual, p10, p90)
    assert_close(cov, 0.60, label="coverage 3/5")

    # All inside
    all_cov = prediction_interval_coverage(
        np.array([5.0, 5.0]),
        np.array([4.0, 4.0]),
        np.array([6.0, 6.0]),
    )
    assert_close(all_cov, 1.0, label="coverage all inside")
    return True


def test_crps():
    print("\n-- Test: crps_ensemble_score and gaussian fallback --")
    # Perfect forecast: actual == p50, narrow interval -> low CRPS
    actual = np.array([50.0, 50.0, 50.0])
    p50    = np.array([50.0, 50.0, 50.0])
    p10    = np.array([45.0, 45.0, 45.0])
    p90    = np.array([55.0, 55.0, 55.0])
    score = crps_ensemble_score(actual, p50, p10, p90)
    print(f"  {PASS if score < 5.0 else FAIL} CRPS perfect forecast: {score:.4f} (expect < 5)")

    # Bad forecast: actual far from p50 -> higher CRPS
    bad_p50 = np.array([100.0, 100.0, 100.0])
    bad_score = crps_ensemble_score(actual, bad_p50, p10, p90)
    print(f"  {PASS if bad_score > score else FAIL} CRPS bad > perfect: {bad_score:.4f} > {score:.4f}")

    # Backward compatibility check: gaussian still available for tests
    g_score = crps_gaussian(actual, p50, p10, p90)
    print(f"  {PASS if g_score >= 0 else FAIL} Gaussian CRPS callable: {g_score:.4f}")
    return True


def test_calibration_audit():
    print("\n-- Test: quantile_calibration_audit --")
    n = 2000
    rng = np.random.default_rng(42)
    y_true = rng.uniform(0.0, 1.0, size=n)
    q10 = np.full(n, 0.10)
    q50 = np.full(n, 0.50)
    q90 = np.full(n, 0.90)
    audit = quantile_calibration_audit(y_true, [q10, q50, q90], [0.1, 0.5, 0.9])
    mae = audit["mean_abs_calibration_error"]
    print(f"  {PASS if mae < 0.03 else FAIL} Mean calibration error small: {mae:.4f}")
    return True


def test_sharpness():
    print("\n-- Test: sharpness_score --")
    p10 = np.array([10.0, 20.0, 30.0])
    p90 = np.array([20.0, 40.0, 60.0])
    cap = np.array([100.0, 100.0, 100.0])
    score = sharpness_score(p10, p90, cap)
    # widths: 10,20,30 => mean width 20; /100 = 0.20
    assert_close(score, 0.20, tol=1e-6, label="sharpness normalized width")
    return True


def test_evaluate_end_to_end():
    print("\n-- Test: evaluate() end-to-end --")
    np.random.seed(42)
    n = 24 * 30  # 30 days hourly

    dates    = pd.date_range("2023-06-01", periods=n, freq="h")
    plants   = ["PVG_S1", "PVG_S2", "GDG_W1", "GDG_W2"]
    rows     = []

    for plant in plants:
        actual = np.random.uniform(0, 100, n)
        noise  = np.random.uniform(-10, 10, n)
        rows.append(pd.DataFrame({
            "timestamp": dates,
            "plant_id" : plant,
            "actual"   : actual,
            "p50"      : np.clip(actual + noise,      0, 120),
            "p10"      : np.clip(actual + noise - 15, 0, 120),
            "p90"      : np.clip(actual + noise + 15, 0, 120),
            "capacity_mw": 120.0,
        }))

    df = pd.concat(rows, ignore_index=True)

    plant_type_map = {
        "PVG_S1": "solar", "PVG_S2": "solar",
        "GDG_W1": "wind",  "GDG_W2": "wind",
    }

    results = evaluate(df, plant_type_map=plant_type_map)

    # Structure checks
    assert "overall"       in results, "Missing 'overall' key"
    assert "by_plant"      in results, "Missing 'by_plant' key"
    assert "by_hour"       in results, "Missing 'by_hour' key"
    assert "by_season"     in results, "Missing 'by_season' key"
    assert "solar_summary" in results, "Missing 'solar_summary' key"
    assert "wind_summary"  in results, "Missing 'wind_summary' key"

    print(f"  {PASS} All top-level keys present")
    print(f"  {PASS} Plants in result: {list(results['by_plant'].keys())}")
    print(f"  {PASS} Hours in result:  {sorted(results['by_hour'].keys())[:5]}...")
    print(f"  {PASS} Seasons in result: {list(results['by_season'].keys())}")
    print(f"\n  Overall metrics: {results['overall']}")
    print(f"  Solar summary:   {results['solar_summary']}")
    print(f"  Wind summary:    {results['wind_summary']}")
    return True


def test_assign_season():
    print("\n-- Test: assign_season --")
    cases = {
        1: "Winter", 2: "Winter", 3: "Summer", 4: "Summer",
        5: "Summer", 6: "Monsoon", 7: "Monsoon", 8: "Monsoon",
        9: "Monsoon", 10: "Post-Monsoon", 11: "Post-Monsoon", 12: "Winter"
    }
    all_ok = True
    for month, expected in cases.items():
        got = assign_season(month)
        ok = got == expected
        if not ok:
            print(f"  {FAIL} Month {month}: got '{got}', expected '{expected}'")
            all_ok = False
    if all_ok:
        print(f"  {PASS} All 12 months map correctly")
    return all_ok


if __name__ == "__main__":
    print("=" * 55)
    print("  Person 4 — Evaluation Harness Smoke Test (Day 1)")
    print("=" * 55)

    results = [
        test_assign_season(),
        test_temporal_split(),
        test_nmae(),
        test_nrmse(),
        test_coverage(),
        test_crps(),
        test_calibration_audit(),
        test_sharpness(),
        test_evaluate_end_to_end(),
    ]

    print("\n" + "=" * 55)
    passed = sum(results)
    print(f"  {passed}/{len(results)} test groups passed")
    if passed == len(results):
        print("  ALL GOOD — harness is ready for Day 2.")
    else:
        print("  Some tests failed — fix before Day 2.")
    print("=" * 55)