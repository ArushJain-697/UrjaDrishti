import pandas as pd

_ID_COLS    = ['timestamp', 'plant_id', 'cluster_id']
_TARGET     = 'actual_generation_mw'

_CAT_MAP    = {'solar': 0, 'wind': 1}

FEATURE_COLS = [
    # Physics outputs
    'CMF',
    'power_curve_fraction',
    # Weather
    'temperature',
    'nwp_spread',
    # Asset metadata  (global model: tells LightGBM which plant it is)
    'capacity_mw',
    'lat_sin',
    'lat_cos',
    'lon_sin',
    'lon_cos',
    'tilt_angle_deg',
    'hub_height_m',
    # Time encodings
    'hour_sin',
    'hour_cos',
    'doy_sin',
    'doy_cos',
    'season',
    # Plant type (encoded)
    'plant_type_enc',
]

"""
    Prepare the feature matrix for model training / inference.
    Steps:
    1. Encode plant_type → integer (solar=0, wind=1)
    2. Drop non-feature identifier columns
    3. Return X (features DataFrame) and y (Series) if target present
"""
def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Encode plant type
    df['plant_type_enc'] = df['plant_type'].map(_CAT_MAP).fillna(-1).astype(int)

    # 2. Separate X and y
    X = df[FEATURE_COLS].copy()

    if _TARGET in df.columns:
        y = df[_TARGET].copy()
    else:
        y = None

    return X, y


def get_feature_names():
    """Return the ordered list of feature column names used by the model."""
    return FEATURE_COLS.copy()
