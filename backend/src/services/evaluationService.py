# Once Person 4 finishes, uncomment this
# from src.ml.evaluation.metrics import get_results as ml_results

MOCK_EVALUATION = {
    "baselines": {
        "persistence":     {"nmae_solar": 0.21, "nmae_wind": 0.24, "crps": 0.33},
        "climatological":  {"nmae_solar": 0.17, "nmae_wind": 0.20, "crps": 0.29},
        "raw_nwp":         {"nmae_solar": 0.15, "nmae_wind": 0.18, "crps": 0.26},
    },
    "model": {"nmae_solar": 0.09, "nmae_wind": 0.11, "crps": 0.14},
    "improvement_over_persistence": {
        "nmae_solar_pct": 57,
        "nmae_wind_pct":  54,
        "crps_pct":       58
    }
}

def get_evaluation():
    try:
        # return ml_results()
        return MOCK_EVALUATION
    except Exception as e:
        print(f"Evaluation error: {e} — falling back to mock")
        return MOCK_EVALUATION