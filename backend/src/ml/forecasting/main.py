"""
main.py — UrjaDrishti forecasting pipeline (Day 3).

Runs:
  1. Stage-1 global model training (Day-2 baseline).
  2. Stage-2 residual corrector training on val-set predictions.
  3. Evaluation: Stage-1 vs Stage-2 on the held-out test set.
  4. Intra-day simulation at cutoff_hour=12 to verify Stage-2 improves
     afternoon forecasts when morning actuals are fed in.
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd

from data_loader         import load_data, temporal_split
from feature_engineering import transform
from model               import (
    train_stage1, predict_stage1,
    build_stage2_training_data, train_stage2,
    intraday_update,
    save_model, load_model,
)
from evaluation import nMAE, nRMSE

_HERE        = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CSV = os.path.join(_HERE, '..', 'data', 'feature_matrix_final.csv')


def _cap_map(df):
    return df.groupby('plant_id')['capacity_mw'].first().to_dict()


def _total_cap(cap):
    return sum(cap.values()) if cap else 1.0


# ---------------------------------------------------------------------------
# Stage-1: global day-ahead model
# ---------------------------------------------------------------------------
def train_and_eval_stage1(train_df, val_df, test_df):
    X_train, y_train = transform(train_df)
    X_val,   y_val   = transform(val_df)
    X_test,  y_test  = transform(test_df)

    s1 = train_stage1(X_train, y_train, X_val, y_val)

    cap   = _cap_map(test_df)
    cap_t = _total_cap(cap)
    preds = predict_stage1(s1, X_test)

    print(f"[Stage-1]  nMAE={nMAE(y_test, preds, cap_t):.4f}  "
          f"nRMSE={nRMSE(y_test, preds, cap_t):.4f}")

    return s1, preds, y_test, X_test


# ---------------------------------------------------------------------------
# Stage-2: build training data from val-set residuals, train corrector
# ---------------------------------------------------------------------------
def prepare_stage2_data(s1_model, df_slice, label):
    """
    Attach Stage-1 predictions to df_slice, then call build_stage2_training_data.
    df_slice must contain all feature columns + actual_generation_mw + timestamp + plant_id.
    """
    X, _ = transform(df_slice)
    s1_preds = predict_stage1(s1_model, X)

    enriched = df_slice[[
        'timestamp', 'plant_id', 'actual_generation_mw',
        'CMF', 'power_curve_fraction',
        'capacity_mw', 'lat_sin', 'lat_cos', 'lon_sin', 'lon_cos',
    ]].copy()
    enriched['s1_pred'] = s1_preds

    X2, y2 = build_stage2_training_data(enriched)
    print(f"[Stage-2 {label}] rows={len(X2):,}")
    return X2, y2


def train_and_eval_stage2(s1_model, val_df, test_df):
    X2_train, y2_train = prepare_stage2_data(s1_model, val_df,  "train")
    X2_val,   y2_val   = prepare_stage2_data(s1_model, test_df, "val")

    s2 = train_stage2(X2_train, y2_train, X2_val, y2_val)
    return s2


# ---------------------------------------------------------------------------
# Evaluation: Stage-2 corrected predictions on full test set
# (simulate cutoff at every hour for an unbiased estimate)
# ---------------------------------------------------------------------------
def eval_stage2_full(s1_model, s2_model, test_df):
    """
    For each (plant, day) in test_df, simulate intra-day update at hour 12
    and collect corrected predictions for hours ≥12.
    Compare s1 vs s2 on those future hours.
    """
    test_df = test_df.copy()
    test_df['date'] = test_df['timestamp'].dt.date

    s1_errors, s2_errors, actuals = [], [], []

    for (plant_id, date), day_df in test_df.groupby(['plant_id', 'date']):
        if len(day_df) < 13:
            continue  # need at least some morning hours

        result = intraday_update(s1_model, s2_model, day_df, cutoff_hour=12)
        future = result[result['hour_of_day'] >= 12]

        # Only evaluate hours where actual is known
        known = future.dropna(subset=['actual'])
        if known.empty:
            continue

        s1_errors.extend(np.abs(known['actual'] - known['s1_pred']).tolist())
        s2_errors.extend(np.abs(known['actual'] - known['final_pred']).tolist())
        actuals.extend(known['actual'].tolist())

    cap_t = _total_cap(_cap_map(test_df))

    s1_nmae = np.mean(s1_errors) / cap_t
    s2_nmae = np.mean(s2_errors) / cap_t
    improvement = (s1_nmae - s2_nmae) / s1_nmae * 100

    print(f"[Intra-day @12h]  Stage-1 nMAE={s1_nmae:.4f}  "
          f"Stage-2 nMAE={s2_nmae:.4f}  "
          f"Improvement={improvement:+.1f}%")

    return s1_nmae, s2_nmae


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(data_path):
    df = load_data(data_path)
    train_df, val_df, test_df = temporal_split(df, val_months=2, test_months=2)

    # --- Stage 1 ---
    s1_model, test_preds, y_test, X_test = train_and_eval_stage1(
        train_df, val_df, test_df
    )

    # --- Stage 2 ---
    s2_model = train_and_eval_stage2(s1_model, val_df, test_df)

    # --- Intra-day evaluation ---
    eval_stage2_full(s1_model, s2_model, test_df)

    # --- Save both models ---
    save_model(s1_model, os.path.join(_HERE, 'kredl_stage1.pkl'))
    save_model(s2_model, os.path.join(_HERE, 'kredl_stage2.pkl'))

    return s1_model, s2_model


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='UrjaDrishti Day-3 pipeline')
    parser.add_argument('--data', default=_DEFAULT_CSV)
    args = parser.parse_args()

    if not os.path.exists(args.data):
        print(f"ERROR: Data file not found -> {args.data}")
        sys.exit(1)

    run(args.data)