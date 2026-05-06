"""
Person 4 — Baseline Evaluation Runner (real data only)
======================================================

Runs baseline evaluation on Person 1's `feature_matrix_final.csv` and
`raw_weather_data.csv`. No dummy data/model fallback is used.

Usage (from backend/):
    python -m src.ml.evaluation.test_baselines
"""

from src.ml.evaluation.baselines import run_all_baselines
from src.ml.evaluation.metrics import resolve_evaluation_data_paths


def _fmt(value):
    if value is None:
        return "N/A"
    return f"{value:.4f}"


def main() -> None:
    paths = resolve_evaluation_data_paths()
    feature_path = paths["feature_matrix"]
    weather_path = paths["raw_weather"]

    print(f"[Baselines] feature_matrix: {feature_path}")
    print(f"[Baselines] raw_weather:    {weather_path}")
    results = run_all_baselines(feature_path, weather_path)

    for key in ("persistence", "climatological", "raw_nwp"):
        if key not in results:
            raise RuntimeError(f"Missing baseline key '{key}' in results")
        if "overall" not in results[key]:
            raise RuntimeError(f"Missing '{key}.overall' in results")

    print("\nBaseline comparison on the last 2 months:")
    print("┌─────────────────────┬──────────────┬──────────────┬──────────────┬──────────────┐")
    print("│ Baseline            │ nMAE overall │ nRMSE overall│ CRPS overall │ Coverage 80% │")
    print("├─────────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤")
    for label, key in (
        ("Persistence    ", "persistence"),
        ("Climatological ", "climatological"),
        ("Raw NWP LR     ", "raw_nwp"),
    ):
        overall = results[key]["overall"]
        print(
            f"│ {label} │ {_fmt(overall.get('nmae')):^12} │ {_fmt(overall.get('nrmse')):^12} │ "
            f"{_fmt(overall.get('crps')):^12} │ {_fmt(overall.get('coverage_80')):^12} │"
        )
    print("└─────────────────────┴──────────────┴──────────────┴──────────────┴──────────────┘")


if __name__ == "__main__":
    main()