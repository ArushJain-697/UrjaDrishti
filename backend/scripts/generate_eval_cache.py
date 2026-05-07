"""
Run this script once locally to pre-compute evaluation results and save
them to backend/src/ml/evaluation/_eval_cache.json.

The cache is then loaded by get_results() on the server (Railway), where
the raw data CSV is not available.

Usage (from repo root):
    cd backend
    python -m scripts.generate_eval_cache
"""
import json
import os
import sys

# Ensure src is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ml.evaluation.metrics import (
    get_results,
    resolve_evaluation_data_paths,
)

CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src", "ml", "evaluation", "_eval_cache.json",
)


def main():
    paths = resolve_evaluation_data_paths()
    feature_path = paths["feature_matrix"]

    if not os.path.exists(feature_path):
        print(f"ERROR: Feature matrix not found at {feature_path}")
        print("Run this script from the repo root where data/ exists.")
        sys.exit(1)

    print("Computing evaluation results (this may take a minute)...")
    results = get_results()

    # Remove non-serializable data (DataFrames etc.) — keep only what the API returns
    def _clean(obj):
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_clean(v) for v in obj]
        if hasattr(obj, 'item'):   # numpy scalar
            return obj.item()
        return obj

    clean_results = _clean(results)
    # Remove the raw model_evaluation DataFrame-derived blob — too large
    clean_results.pop("model_evaluation", None)

    with open(CACHE_PATH, "w") as f:
        json.dump(clean_results, f, indent=2)

    print(f"\nCache saved to: {CACHE_PATH}")
    print("Now commit this file and push — Railway will use it automatically.")


if __name__ == "__main__":
    main()
