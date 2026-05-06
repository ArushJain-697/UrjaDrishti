import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

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
_DEFAULT_CSV = os.path.join(_HERE, '..', '..', '..', '..', 'data', 'feature_matrix_final.csv')
_OUT_DIR = os.path.join(_HERE, 'artefacts')
os.makedirs(_OUT_DIR, exist_ok=True)


def _cap_map(df):
    return df.groupby('plant_id')['capacity_mw'].first().to_dict()


def _total_cap(cap):
    return sum(cap.values()) if cap else 1.0


def _season(month):
    return {12: 'Winter', 1: 'Winter', 2: 'Winter',
             3: 'Spring',  4: 'Spring',  5: 'Spring',
             6: 'Summer',  7: 'Summer',  8: 'Summer',
             9: 'Autumn', 10: 'Autumn', 11: 'Autumn'}[month]


def train_and_eval_stage1(train_df, calib_df, val_df, test_df):
    X_train, y_train = transform(train_df)
    X_calib, y_calib = transform(calib_df)
    X_val,   y_val   = transform(val_df)
    X_test,  y_test  = transform(test_df)

    s1 = train_stage1(X_train, y_train, X_calib, y_calib, X_val, y_val)

    cap_t = _total_cap(_cap_map(test_df))
    preds = predict_stage1(s1, X_test)

    print(f"[Stage-1]  nMAE={nMAE(y_test, preds, cap_t):.4f}  "
          f"nRMSE={nRMSE(y_test, preds, cap_t):.4f}")

    return s1, preds, y_test, X_test


def evaluate_coverage(s1_model, test_df, out_dir=_OUT_DIR):
    X_test, y_test = transform(test_df)
    _, p10, p90 = predict_stage1(s1_model, X_test, return_pis=True)
    y_arr = y_test.values

    covered = (y_arr >= p10) & (y_arr <= p90)

    overall_coverage = float(np.mean(covered))
    print(f"[Coverage]  Overall P10–P90 coverage = {overall_coverage:.3f}  "
          f"(target ≈ 0.800)")

    test_meta = test_df.reset_index(drop=True)
    test_meta['covered'] = covered

    plant_cov = (
        test_meta.groupby('plant_id')['covered']
        .mean()
        .sort_values()
        .reset_index()
    )
    plant_cov.columns = ['plant_id', 'coverage']

    fig, ax = plt.subplots(figsize=(max(8, len(plant_cov) * 0.55), 5))
    ax.bar(plant_cov['plant_id'], plant_cov['coverage'],
           color='steelblue', edgecolor='white', linewidth=0.6)
    ax.axhline(0.80, color='tomato', linestyle='--', linewidth=1.5, label='Target 80 %')
    ax.axhline(overall_coverage, color='gold', linestyle='-', linewidth=1.5,
               label=f'Overall {overall_coverage:.1%}')
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1))
    ax.set_xlabel('Plant ID', fontsize=11)
    ax.set_ylabel('P10–P90 Coverage', fontsize=11)
    ax.set_title('Empirical Coverage per Plant (MAPIE CQR, α=0.2)', fontsize=13)
    plt.xticks(rotation=45, ha='right', fontsize=8)
    ax.legend()
    fig.tight_layout()
    plant_plot_path = os.path.join(out_dir, 'coverage_per_plant.png')
    fig.savefig(plant_plot_path, dpi=150)
    plt.close(fig)
    print(f"  → Saved {plant_plot_path}")

    test_meta['season'] = test_meta['timestamp'].dt.month.map(_season)

    season_order = ['Spring', 'Summer', 'Autumn', 'Winter']
    season_cov = (
        test_meta.groupby('season')['covered']
        .mean()
        .reindex(season_order)
        .reset_index()
    )
    season_cov.columns = ['season', 'coverage']

    palette = ['#4CAF50', '#FF9800', '#F44336', '#2196F3']
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(season_cov['season'], season_cov['coverage'],
           color=palette, edgecolor='white', linewidth=0.8, width=0.55)
    ax.axhline(0.80, color='tomato', linestyle='--', linewidth=1.5, label='Target 80 %')
    ax.axhline(overall_coverage, color='gold', linestyle='-', linewidth=1.5,
               label=f'Overall {overall_coverage:.1%}')
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1))
    ax.set_xlabel('Season', fontsize=11)
    ax.set_ylabel('P10–P90 Coverage', fontsize=11)
    ax.set_title('Empirical Coverage per Season (MAPIE CQR, α=0.2)', fontsize=13)
    ax.legend()
    fig.tight_layout()
    season_plot_path = os.path.join(out_dir, 'coverage_per_season.png')
    fig.savefig(season_plot_path, dpi=150)
    plt.close(fig)
    print(f"  → Saved {season_plot_path}")

    return overall_coverage


def prepare_stage2_data(s1_model, df_slice, label):
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


def eval_stage2_full(s1_model, s2_model, test_df):
    test_df = test_df.copy()
    test_df['date'] = test_df['timestamp'].dt.date

    s1_errors, s2_errors = [], []

    for (plant_id, date), day_df in test_df.groupby(['plant_id', 'date']):
        if len(day_df) < 13:
            continue

        day_df = day_df.copy()
        result = intraday_update(s1_model, s2_model, day_df, cutoff_hour=12)
        future = result[result['hour_of_day'] >= 12]
        known  = future.dropna(subset=['actual'])
        if known.empty:
            continue

        s1_errors.extend(np.abs(known['actual'] - known['s1_pred']).tolist())
        s2_errors.extend(np.abs(known['actual'] - known['final_pred']).tolist())

    cap_t = _total_cap(_cap_map(test_df))

    s1_nmae = np.mean(s1_errors) / cap_t
    s2_nmae = np.mean(s2_errors) / cap_t
    improvement = (s1_nmae - s2_nmae) / s1_nmae * 100

    print(f"[Intra-day @12h]  Stage-1 nMAE={s1_nmae:.4f}  "
          f"Stage-2 nMAE={s2_nmae:.4f}  "
          f"Improvement={improvement:+.1f}%")

    return s1_nmae, s2_nmae


def run(data_path):
    df = load_data(data_path)

    train_df, calib_df, val_df, test_df = temporal_split(
        df, calib_months=3, val_months=2, test_months=2
    )

    s1_model, test_preds, y_test, X_test = train_and_eval_stage1(
        train_df, calib_df, val_df, test_df
    )

    evaluate_coverage(s1_model, test_df)

    s2_model = train_and_eval_stage2(s1_model, val_df, test_df)

    eval_stage2_full(s1_model, s2_model, test_df)

    save_model(s1_model, os.path.join(_HERE, 'kredl_stage1.pkl'))
    save_model(s2_model, os.path.join(_HERE, 'kredl_stage2.pkl'))
    print("[Saved]  kredl_stage1.pkl  kredl_stage2.pkl")

    return s1_model, s2_model


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='UrjaDrishti Day-4/5 pipeline')
    parser.add_argument('--data', default=_DEFAULT_CSV)
    args = parser.parse_args()

    if not os.path.exists(args.data):
        print(f"ERROR: Data file not found -> {args.data}")
        sys.exit(1)

    run(args.data)