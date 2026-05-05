"""
Person 4 Day 5: Final evaluation report artifact generator.

Usage (from backend/):
    python scripts/evaluation/run_day5_report.py
"""

from pathlib import Path

import pandas as pd

from src.ml.evaluation.baselines import PLANT_TYPE_MAP
from src.ml.evaluation.metrics import (
    _build_model_test_forecast,
    evaluate,
    get_results,
    plot_quantile_reliability,
    resolve_evaluation_data_paths,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _reports_dir() -> Path:
    out = _repo_root() / "backend" / "reports" / "evaluation"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _evaluation_plots_dir() -> Path:
    out = _repo_root() / "data" / "evaluation_plots"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _model_row(model_dict: dict) -> dict:
    return {
        "model": "LightGBM (ours)",
        "nmae_solar": model_dict.get("nmae_solar"),
        "nmae_wind": model_dict.get("nmae_wind"),
        "nrmse_solar": model_dict.get("nrmse_solar"),
        "nrmse_wind": model_dict.get("nrmse_wind"),
        "crps": model_dict.get("crps"),
        "coverage_80": model_dict.get("coverage_80"),
        "sharpness": model_dict.get("sharpness"),
    }


def _baseline_rows(baselines: dict) -> list[dict]:
    name_map = {
        "persistence": "Persistence",
        "climatological": "Climatological",
        "raw_nwp": "Raw NWP LR",
    }
    rows = []
    for key in ["persistence", "climatological", "raw_nwp"]:
        b = baselines.get(key, {})
        rows.append(
            {
                "model": name_map[key],
                "nmae_solar": b.get("nmae_solar"),
                "nmae_wind": b.get("nmae_wind"),
                "nrmse_solar": b.get("nrmse_solar"),
                "nrmse_wind": b.get("nrmse_wind"),
                "crps": b.get("crps"),
                "coverage_80": b.get("coverage_80"),
                "sharpness": b.get("sharpness"),
            }
        )
    return rows


def _write_submission_markdown(
    out_md: Path,
    comparison_df: pd.DataFrame,
    season_df: pd.DataFrame,
    calm_width_mw: float | None,
    peak_stress_width_mw: float | None,
) -> None:
    lines = []
    lines.append("# Person 4 Day 5 Evaluation Report")
    lines.append("")
    lines.append("## Model vs Baseline Comparison")
    lines.append("")
    lines.append(comparison_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Calibration Chart")
    lines.append("")
    lines.append("- Reliability diagram: `data/evaluation_plots/quantile_reliability.png`")
    lines.append("")
    lines.append("## Interval Width Contrast")
    lines.append("")
    if calm_width_mw is not None and peak_stress_width_mw is not None:
        lines.append(f"- Calm test mean interval width (MW): **{calm_width_mw:.3f}**")
        lines.append(f"- Peak stress mean interval width (MW): **{peak_stress_width_mw:.3f}**")
        if calm_width_mw > 0:
            lines.append(f"- Widening factor (stress / calm): **{(peak_stress_width_mw / calm_width_mw):.2f}x**")
    else:
        lines.append("- Day 4 stress summary missing; run `scripts/evaluation/run_stress_evaluation.py` first.")
    lines.append("- Contrast plot: `data/evaluation_plots/calm_vs_stress_interval_width.png`")
    lines.append("")
    lines.append("## Season-Stratified Performance")
    lines.append("")
    lines.append(season_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Evaluator FAQ (One-line Answers)")
    lines.append("")
    lines.append("- Why is monsoon accuracy lower? -> Fast cloud and wind transitions increase atmospheric uncertainty and reduce point predictability.")
    lines.append("- How were baselines implemented? -> Persistence uses 24h lag, climatological uses train-only plant-hour-month means, raw NWP LR is per-plant linear regression on raw weather.")
    lines.append("- What does CRPS mean? -> CRPS scores the full predictive distribution, jointly rewarding accurate medians and well-calibrated uncertainty intervals.")
    lines.append("- Why rolling holdout instead of random split? -> Rolling temporal holdout prevents leakage from future into past and matches real forecasting deployment.")
    lines.append("")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    reports_dir = _reports_dir()
    plot_dir = _evaluation_plots_dir()

    results = get_results()
    baselines = results.get("baselines", {})
    model = results.get("model", {})
    model_evaluation = results.get("model_evaluation") or {}

    comparison_rows = _baseline_rows(baselines) + [_model_row(model)]
    comparison_df = pd.DataFrame(comparison_rows)
    comparison_df.to_csv(reports_dir / "comparison_table.csv", index=False)

    # Feature 5: calibration audit + reliability plot
    calibration = model_evaluation.get("quantile_calibration")
    if calibration:
        pd.DataFrame(calibration.get("points", [])).to_csv(
            reports_dir / "quantile_calibration_points.csv", index=False
        )
        plot_quantile_reliability(calibration, str(plot_dir / "quantile_reliability.png"))

    # Season table export
    by_season = model_evaluation.get("by_season", {})
    season_rows = [
        {"season": season, "nmae": vals.get("nmae"), "nrmse": vals.get("nrmse"), "crps": vals.get("crps")}
        for season, vals in by_season.items()
    ]
    season_df = pd.DataFrame(season_rows).sort_values("season") if season_rows else pd.DataFrame(
        columns=["season", "nmae", "nrmse", "crps"]
    )
    season_df.to_csv(reports_dir / "season_stratified_table.csv", index=False)

    # Feature 10: sharpness surfaced in comparison table + calm baseline width
    calm_width_mw = None
    peak_stress_width_mw = None
    paths = resolve_evaluation_data_paths()
    model_test_df = _build_model_test_forecast(paths["feature_matrix"])
    if model_test_df is not None:
        calm_width_mw = float((model_test_df["p90"] - model_test_df["p10"]).mean())
        calm_eval = evaluate(model_test_df, plant_type_map=PLANT_TYPE_MAP)
        pd.DataFrame([{"split": "normal_test", "sharpness": calm_eval.get("overall", {}).get("sharpness")}]).to_csv(
            reports_dir / "sharpness_summary.csv", index=False
        )

    stress_summary_path = plot_dir / "stress_metrics_summary.csv"
    if stress_summary_path.exists():
        stress_df = pd.read_csv(stress_summary_path)
        if not stress_df.empty and "mean_interval_width_mw" in stress_df.columns:
            peak_stress_width_mw = float(stress_df["mean_interval_width_mw"].max())

    report_md = reports_dir / "evaluation_section.md"
    _write_submission_markdown(
        report_md,
        comparison_df,
        season_df,
        calm_width_mw,
        peak_stress_width_mw,
    )
    print(f"[Day5] Wrote report artifacts to {reports_dir}")


if __name__ == "__main__":
    main()
