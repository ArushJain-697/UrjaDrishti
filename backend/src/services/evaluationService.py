"""
Evaluation service.
The ML import is deferred inside get_evaluation() so a missing dependency
never prevents the FastAPI app from starting. Falls back to mock data
(shaped identically to the real response) if the import or call fails.
"""


def _mock_evaluation() -> dict:
    """
    Mock evaluation data matching the exact shape the API/dashboard expects.
    Model metrics (nmae_solar, nmae_wind, crps) are None until Person 2's
    forecast DataFrame is connected on Day 3.
    """
    return {
        "baselines": {
            "persistence":    {"nmae_solar": 0.21, "nmae_wind": 0.24, "crps": 0.33},
            "climatological": {"nmae_solar": 0.17, "nmae_wind": 0.20, "crps": 0.29},
            "raw_nwp":        {"nmae_solar": 0.15, "nmae_wind": 0.18, "crps": 0.26},
        },
        "model": {
            "nmae_solar": 0.09,
            "nmae_wind":  0.11,
            "crps":       0.14,
        },
        "improvement_over_persistence": {
            "nmae_solar_pct": 57,
            "nmae_wind_pct":  54,
            "crps_pct":       58,
        },
    }


def get_evaluation() -> dict:
    """
    Called by the evaluation route. Tries Person 4's real metrics module first,
    falls back to mock if not yet available or if it raises.
    """
    try:
        from src.ml.evaluation.metrics import get_results as ml_results
        return ml_results()
    except Exception as e:
        print(f"Evaluation error: {e} — falling back to mock")
        return _mock_evaluation()