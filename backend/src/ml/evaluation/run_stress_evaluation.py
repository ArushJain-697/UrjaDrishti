"""
Evaluate stress scenarios with Stage-1 model and export plots/tables.

Usage (from backend/):
    python -m src.ml.evaluation.run_stress_evaluation
"""

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.ml.evaluation.baselines import PLANT_TYPE_MAP
from src.ml.evaluation.metrics import (
    assign_season,
    evaluate,
    prediction_interval_coverage,
    resolve_evaluation_data_paths,
    sharpness_score,
    temporal_split,
)
from src.ml.forecasting.feature_engineering import transform
from src.ml.forecasting.model import predict_stage1
from src.ml.forecasting.predict import _STAGE1_PATH


STRESS_FILES = [
    "stress_cloud_ramp.csv",
    "stress_monsoon_onset.csv",
    "stress_wind_spike.csv",
    "stress_low_irradiance.csv",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _data_dir() -> Path:
    return _repo_root() / "data"


def _plot_dir() -> Path:
    out = _data_dir() / "evaluation_plots"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _predict_with_stage1(df: pd.DataFrame, model) -> pd.DataFrame:
    X, _ = transform(df)
    p50, p10, p90 = predict_stage1(model, X, return_pis=True)
    out = df.copy()
    out["p50"] = p50
    out["p10"] = p10
    out["p90"] = p90
    return out


def _scenario_metrics(df: pd.DataFrame) -> dict:
    actual = df["actual_generation_mw"].values
    p50 = df["p50"].values
    p10 = df["p10"].values
    p90 = df["p90"].values
    cap = df["capacity_mw"].values if "capacity_mw" in df.columns else np.ones(len(df))
    width = p90 - p10
    return {
        "n_samples": int(len(df)),
        "nmae": float(np.round(np.mean(np.abs(actual - p50)) / np.mean(actual), 4)) if np.mean(actual) else np.nan,
        "coverage_80": float(np.round(prediction_interval_coverage(actual, p10, p90), 4)),
        "mean_interval_width_mw": float(np.round(np.mean(width), 4)),
        "sharpness": float(np.round(sharpness_score(p10, p90, cap), 4)),
    }


def _plot_cloud_ramp(df: pd.DataFrame, out_dir: Path) -> None:
    if "hour_in_event" not in df.columns:
        return
    plot_df = df.groupby("hour_in_event", as_index=False).agg(width=("p90", "mean"))
    plot_df["width"] = (
        df.groupby("hour_in_event")["p90"].mean() - df.groupby("hour_in_event")["p10"].mean()
    ).values
    plt.figure(figsize=(10, 4))
    plt.plot(plot_df["hour_in_event"], plot_df["width"], marker="o")
    plt.axvspan(10, 11, color="red", alpha=0.15, label="Cloud front (hrs 10-11)")
    plt.title("Cloud ramp: interval width vs hour_in_event")
    plt.xlabel("hour_in_event")
    plt.ylabel("mean interval width (MW)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "cloud_ramp_interval_width.png", dpi=140)
    plt.close()


def _plot_monsoon(df: pd.DataFrame, out_dir: Path) -> None:
    key = "day_in_event" if "day_in_event" in df.columns else "timestamp"
    agg = df.groupby(key).agg(width=("p90", "mean"))
    agg["width"] = df.groupby(key)["p90"].mean() - df.groupby(key)["p10"].mean()
    plt.figure(figsize=(10, 4))
    plt.plot(agg.index, agg["width"].values)
    plt.title("Monsoon onset: interval width trend")
    plt.xlabel(key)
    plt.ylabel("mean interval width (MW)")
    plt.tight_layout()
    plt.savefig(out_dir / "monsoon_onset_interval_width.png", dpi=140)
    plt.close()


def _plot_wind_spike(df: pd.DataFrame, out_dir: Path) -> None:
    x_col = "wind_speed_ms" if "wind_speed_ms" in df.columns else "power_curve_fraction"
    width = df["p90"] - df["p10"]
    plt.figure(figsize=(8, 5))
    plt.scatter(df[x_col], width, alpha=0.5)
    if x_col == "wind_speed_ms":
        plt.axvspan(22, 27, color="orange", alpha=0.15, label="22-27 m/s")
        plt.legend()
    plt.title("Wind spike: interval width vs wind speed")
    plt.xlabel(x_col)
    plt.ylabel("interval width (MW)")
    plt.tight_layout()
    plt.savefig(out_dir / "wind_spike_width_vs_wind.png", dpi=140)
    plt.close()


def _plot_calm_vs_stress(stress_df: pd.DataFrame, normal_test_df: pd.DataFrame, out_dir: Path) -> None:
    stress_width = (stress_df["p90"] - stress_df["p10"]).values
    calm_width = (normal_test_df["p90"] - normal_test_df["p10"]).values
    calm_sample = np.random.default_rng(42).choice(calm_width, size=min(len(stress_width), len(calm_width)), replace=False)
    plt.figure(figsize=(7, 4))
    plt.boxplot([calm_sample, stress_width], labels=["Calm baseline", "Peak stress"])
    plt.title("Calm vs stress interval-width contrast")
    plt.ylabel("interval width (MW)")
    plt.tight_layout()
    plt.savefig(out_dir / "calm_vs_stress_interval_width.png", dpi=140)
    plt.close()


def _season_table(normal_test_pred: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    eval_df = normal_test_pred.rename(columns={"actual_generation_mw": "actual"})
    eval_df["season_label"] = pd.to_datetime(eval_df["timestamp"]).dt.month.apply(assign_season)
    stats = evaluate(eval_df, plant_type_map=PLANT_TYPE_MAP).get("by_season", {})
    table = pd.DataFrame(
        [{"season": season, "nmae": values.get("nmae")} for season, values in stats.items()]
    ).sort_values("season")
    table.to_csv(out_dir / "season_nmae_table.csv", index=False)
    return table


def main() -> None:
    data_dir = _data_dir()
    out_dir = _plot_dir()
    paths = resolve_evaluation_data_paths()
    feature_path = Path(paths["feature_matrix"])

    if not Path(_STAGE1_PATH).exists():
        raise SystemExit(
            f"Missing model file: {_STAGE1_PATH}. Train/export stage-1 model before stress evaluation."
        )

    stage1 = joblib.load(_STAGE1_PATH)
    all_rows = []

    print("[StressEval] Running stress scenario evaluation...")
    for file_name in STRESS_FILES:
        csv_path = data_dir / file_name
        if not csv_path.exists():
            print(f"[StressEval] Skipping missing file: {csv_path}")
            continue
        df = pd.read_csv(csv_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        pred_df = _predict_with_stage1(df, stage1)
        metric_row = {"scenario": file_name.replace(".csv", ""), **_scenario_metrics(pred_df)}
        all_rows.append(metric_row)

        if "cloud_ramp" in file_name:
            _plot_cloud_ramp(pred_df, out_dir)
        elif "monsoon_onset" in file_name:
            _plot_monsoon(pred_df, out_dir)
        elif "wind_spike" in file_name:
            _plot_wind_spike(pred_df, out_dir)

    if not all_rows:
        raise SystemExit("No stress files found.")

    summary = pd.DataFrame(all_rows)
    summary.to_csv(out_dir / "stress_metrics_summary.csv", index=False)

    if not feature_path.exists():
        raise SystemExit(f"Feature matrix missing at {feature_path}")

    base = pd.read_csv(feature_path)
    base["timestamp"] = pd.to_datetime(base["timestamp"])
    _, _, test_df = temporal_split(base, timestamp_col="timestamp")
    normal_pred = _predict_with_stage1(test_df.copy(), stage1)
    _season_table(normal_pred, out_dir)

    peak_stress_name = summary.sort_values("mean_interval_width_mw", ascending=False)["scenario"].iloc[0]
    peak_stress_df = pd.read_csv(data_dir / f"{peak_stress_name}.csv")
    peak_stress_df["timestamp"] = pd.to_datetime(peak_stress_df["timestamp"], utc=True)
    peak_stress_pred = _predict_with_stage1(peak_stress_df, stage1)
    _plot_calm_vs_stress(peak_stress_pred, normal_pred, out_dir)

    methodology = (
        "Calm-vs-stress contrast uses temporal test holdout predictions as calm baseline and the stress "
        "scenario with highest mean interval width as peak-stress sample. We compare interval-width "
        "distributions via boxplot to visualize uncertainty widening under stress."
    )
    (out_dir / "contrast_methodology.md").write_text(methodology + "\n", encoding="utf-8")
    print(summary.to_string(index=False))
    print(f"[StressEval] Artifacts written to: {out_dir}")


if __name__ == "__main__":
    main()
