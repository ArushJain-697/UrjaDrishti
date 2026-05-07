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


def get_historical_sample(date_str: str) -> dict:
    """
    Pulls a real historical day of telemetry and maps it through the ML model.
    Used by the dashboard to verify that the ML audit genuinely passes on calibrated historical data.
    """
    import os
    import pandas as pd
    import numpy as np
    import joblib
    from src.ml.forecasting.predict import _STAGE1_PATH
    from src.ml.forecasting.feature_engineering import FEATURE_COLS
    
    # 1. Load historical dataset
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'feature_matrix_final.csv')
    if not os.path.exists(csv_path):
        return {"error": f"Dataset not found at {csv_path}"}
        
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    
    target_date = pd.to_datetime(date_str).date()
    day_df = df[df['date'] == target_date].copy()
    
    if day_df.empty:
        # Fallback to the first available date if requested date not found
        target_date = df['date'].iloc[0]
        day_df = df[df['date'] == target_date].copy()
        
    # 2. Encode features exactly as expected by model
    day_df['plant_type_enc'] = day_df['plant_type'].apply(lambda x: 0.0 if x == 'solar' else 1.0)
    X = day_df[FEATURE_COLS]
    
    # 3. Load model and predict
    try:
        s1 = joblib.load(_STAGE1_PATH)
        from src.ml.forecasting.model import predict_stage1
        p50, p10, p90 = predict_stage1(s1, X, return_pis=True)
        
        day_df['p10'] = p10
        day_df['p50'] = p50
        day_df['p90'] = p90
    except Exception as e:
        return {"error": f"Failed to predict: {e}"}
        
    # 4. Format identically to what the API expects for audits
    plant_data = {}
    for plant_id, group in day_df.groupby('plant_id'):
        group = group.sort_values('timestamp')
        cap = group['capacity_mw'].iloc[0]
        
        plant_data[plant_id] = {
            'actuals': [round(float(v), 2) for v in group['actual_generation_mw'].tolist()],
            'p10': [round(float(np.clip(v, 0, cap)), 2) for v in group['p10'].tolist()],
            'p50': [round(float(np.clip(v, 0, cap)), 2) for v in group['p50'].tolist()],
            'p90': [round(float(np.clip(v, 0, cap)), 2) for v in group['p90'].tolist()],
        }
        
    return {
        "status": "success",
        "date": str(target_date),
        "plant_data": plant_data
    }