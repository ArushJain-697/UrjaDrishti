import os
import datetime
import numpy as np
import pandas as pd
import joblib

_HERE = os.path.dirname(os.path.abspath(__file__))
_STAGE1_PATH = os.path.join(_HERE, 'kredl_stage1.pkl')
_STAGE2_PATH = os.path.join(_HERE, 'kredl_stage2.pkl')

_ASSET = {
    'PVG_S1': dict(type='solar', capacity_mw=150, lat=14.10, lon=77.28, tilt=18, hub=0),
    'PVG_S2': dict(type='solar', capacity_mw=120, lat=14.12, lon=77.30, tilt=18, hub=0),
    'MIX_S1': dict(type='solar', capacity_mw=90,  lat=14.23, lon=76.40, tilt=20, hub=0),
    'GAD_W1': dict(type='wind',  capacity_mw=100, lat=15.42, lon=75.62, tilt=0,  hub=100),
    'GAD_W2': dict(type='wind',  capacity_mw=80,  lat=15.44, lon=75.64, tilt=0,  hub=100),
    'MIX_W1': dict(type='wind',  capacity_mw=60,  lat=16.20, lon=77.36, tilt=0,  hub=90),
}

_FEATURE_COLS = [
    'CMF', 'power_curve_fraction', 'temperature', 'nwp_spread',
    'capacity_mw', 'lat_sin', 'lat_cos', 'lon_sin', 'lon_cos',
    'tilt_angle_deg', 'hub_height_m',
    'hour_sin', 'hour_cos', 'doy_sin', 'doy_cos', 'season', 'plant_type_enc',
    'wind_speed_ms', 'above_cutout',
]

CUT_IN  = 3.0
CUT_OUT = 25.0

_s1 = None
_s2 = None

def _load_models():
    global _s1, _s2
    if _s1 is None:
        _s1 = joblib.load(_STAGE1_PATH)
    if _s2 is None:
        _s2 = joblib.load(_STAGE2_PATH)
    return _s1, _s2


def _season(month):
    return {12:0,1:0,2:0, 3:1,4:1,5:1, 6:2,7:2,8:2,9:2, 10:3,11:3}[month]


def _build_feature_row(asset, hour, doy, month, cmf_override=None):
    lat_rad = np.radians(asset.get('lat', 14.0))
    lon_rad = np.radians(asset.get('lon', 77.0))

    is_solar = asset['type'] == 'solar'
    solar_angle = max(0.0, np.sin(np.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 0.0
    season_factor = 1.0 + 0.3 * np.sin(2 * np.pi * (doy - 80) / 365)

    if cmf_override is not None:
        cmf = float(cmf_override)
    elif is_solar:
        cmf = float(np.clip(solar_angle * season_factor * 0.82, 0, 1))
    else:
        cmf = 0.0

    wind_speed = 0.0
    above_cutout = 0.0

    if asset['type'] == 'wind':
        seasonal_boost = 0.08 * np.sin(2 * np.pi * (doy - 100) / 365)
        base_pcf = 0.30 + seasonal_boost
        hour_angle = 2 * np.pi * (hour - 14) / 24
        diurnal_pcf = 0.15 * np.cos(hour_angle)
        pcf_raw = float(np.clip(base_pcf + diurnal_pcf, 0.0, 1.0))
        wind_speed = float(3.0 + pcf_raw * 9.0)

        if wind_speed >= CUT_OUT:
            pcf = 0.0
            above_cutout = 1.0
        elif wind_speed < CUT_IN:
            pcf = 0.0
            above_cutout = 0.0
        else:
            pcf = pcf_raw
            above_cutout = 0.0
    else:
        pcf = 0.0

    temperature = 25.0 + 8.0 * np.sin(np.pi * (hour - 4) / 12) + 3.0 * season_factor

    if is_solar:
        nwp_spread = 0.5 + 0.3 * (1 - solar_angle)
    else:
        nwp_spread = 0.6 + 0.4 * abs(np.cos(np.pi * hour / 12))

    return {
        'CMF':                    cmf,
        'power_curve_fraction':   pcf,
        'temperature':            float(temperature),
        'nwp_spread':             float(nwp_spread),
        'capacity_mw':            float(asset['capacity_mw']),
        'lat_sin':                float(np.sin(lat_rad)),
        'lat_cos':                float(np.cos(lat_rad)),
        'lon_sin':                float(np.sin(lon_rad)),
        'lon_cos':                float(np.cos(lon_rad)),
        'tilt_angle_deg':         float(asset['tilt']),
        'hub_height_m':           float(asset['hub']),
        'hour_sin':               float(np.sin(2 * np.pi * hour / 24)),
        'hour_cos':               float(np.cos(2 * np.pi * hour / 24)),
        'doy_sin':                float(np.sin(2 * np.pi * doy / 365)),
        'doy_cos':                float(np.cos(2 * np.pi * doy / 365)),
        'season':                 float(_season(month)),
        'plant_type_enc':         0.0 if is_solar else 1.0,
        'wind_speed_ms':          wind_speed,
        'above_cutout':           above_cutout,
    }


def _make_X(plant_id, hours):
    asset = _ASSET[plant_id]
    now = datetime.datetime.now()
    doy = now.timetuple().tm_yday
    month = now.month
    rows = [_build_feature_row(asset, h, doy, month) for h in hours]
    return pd.DataFrame(rows, columns=_FEATURE_COLS)


def get_forecast(plant_id, hours_of_actuals=0):
    s1, _ = _load_models()
    hours = list(range(24))
    X = _make_X(plant_id, hours)

    from src.ml.forecasting.model import predict_stage1
    p50, p10, p90 = predict_stage1(s1, X, return_pis=True)

    cap = _ASSET[plant_id]['capacity_mw']
    return {
        'plant_id': plant_id,
        'hours':    hours,
        'p50':  [round(float(np.clip(v, 0, cap)), 2) for v in p50],
        'p10':  [round(float(np.clip(v, 0, cap)), 2) for v in p10],
        'p90':  [round(float(np.clip(v, 0, cap)), 2) for v in p90],
    }


def get_intraday_forecast(plant_id, actuals):
    s1, s2 = _load_models()
    hours = list(range(24))
    X = _make_X(plant_id, hours)
    cap = _ASSET[plant_id]['capacity_mw']

    from src.ml.forecasting.model import predict_stage1, intraday_update

    p50_full, p10_full, p90_full = predict_stage1(s1, X, return_pis=True)

    asset = _ASSET[plant_id]
    now = datetime.datetime.now()
    base_date = now.date()

    day_df = pd.DataFrame({
        'timestamp': [pd.Timestamp(f'{base_date} {h:02d}:00:00') for h in hours],
        'plant_id':  plant_id,
        'plant_type': asset['type'],
        'actual_generation_mw': [
            actuals[h] if h < len(actuals) else np.nan
            for h in hours
        ],
        's1_pred': p50_full,
        **{col: X[col].values for col in X.columns},
    })
    day_df['hour_of_day'] = hours

    result = intraday_update(s1, s2, day_df, cutoff_hour=len(actuals))

    cutoff = len(actuals)
    future_p50 = result['final_pred'].values
    p50_full_updated = np.zeros(24)
    for i in range(cutoff):
        p50_full_updated[i] = actuals[i]
    for i in range(cutoff, 24):
        p50_full_updated[i] = future_p50[i - cutoff]

    half_width = (p90_full - p10_full) / 2 * 0.7

    return {
        'plant_id': plant_id,
        'hours':    hours,
        'p50':  [round(float(np.clip(v, 0, cap)), 2) for v in p50_full_updated],
        'p10':  [round(float(np.clip(p50_full_updated[i] - half_width[i], 0, cap)), 2) for i in range(24)],
        'p90':  [round(float(np.clip(p50_full_updated[i] + half_width[i], 0, cap)), 2) for i in range(24)],
    }