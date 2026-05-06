"""
Person 4 — Model Evaluation Harness (real data/model only)
==========================================================

Evaluates Person 2's trained Stage-1 model on the last 2 months of
Person 1's `feature_matrix_final.csv`.

Usage (from backend/):
    python -m src.ml.evaluation.test_harness
"""

import os

import joblib
import pandas as pd

from src.ml.evaluation.baselines import PLANT_TYPE_MAP
from src.ml.evaluation.metrics import evaluate, resolve_evaluation_data_paths, temporal_split
from src.ml.forecasting.feature_engineering import transform
from src.ml.forecasting.model import predict_stage1
from src.ml.forecasting.predict import _STAGE1_PATH


def _load_test_split(feature_matrix_path: str) -> pd.DataFrame:
    df = pd.read_csv(feature_matrix_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    _, _, test_df = temporal_split(df, timestamp_col="timestamp")
    return test_df


def main() -> None:
    paths = resolve_evaluation_data_paths()
    feature_path = paths["feature_matrix"]

    if not os.path.exists(feature_path):
        raise FileNotFoundError(f"Missing feature matrix: {feature_path}")
    if not os.path.exists(_STAGE1_PATH):
        raise FileNotFoundError(f"Missing trained stage-1 model: {_STAGE1_PATH}")

    print(f"[Harness] feature_matrix: {feature_path}")
    print(f"[Harness] stage1_model:   {_STAGE1_PATH}")

    test_df = _load_test_split(feature_path)
    stage1_model = joblib.load(_STAGE1_PATH)
    X_test, _ = transform(test_df)
    p50, p10, p90 = predict_stage1(stage1_model, X_test, return_pis=True)

    eval_df = test_df[["timestamp", "plant_id", "actual_generation_mw", "capacity_mw"]].copy()
    eval_df = eval_df.rename(columns={"actual_generation_mw": "actual"})
    eval_df["p50"] = p50
    eval_df["p10"] = p10
    eval_df["p90"] = p90

    results = evaluate(eval_df, plant_type_map=PLANT_TYPE_MAP, include_coverage_90=True)
    overall = results.get("overall", {})
    solar = results.get("solar_summary", {})
    wind = results.get("wind_summary", {})

    print("\nModel metrics on temporal test split (last 2 months):")
    print(f"- nMAE:       {overall.get('nmae')}")
    print(f"- nRMSE:      {overall.get('nrmse')}")
    print(f"- CRPS:       {overall.get('crps')}")
    print(f"- Coverage80: {overall.get('coverage_80')}")
    print(f"- Sharpness:  {overall.get('sharpness')}")

    print("\nSolar summary:")
    print(f"- nMAE: {solar.get('nmae')}, nRMSE: {solar.get('nrmse')}, CRPS: {solar.get('crps')}")

    print("Wind summary:")
    print(f"- nMAE: {wind.get('nmae')}, nRMSE: {wind.get('nrmse')}, CRPS: {wind.get('crps')}")


if __name__ == "__main__":
    main()