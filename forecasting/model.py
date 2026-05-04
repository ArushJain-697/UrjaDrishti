import numpy as np
import lightgbm as lgb
import joblib

_BASE_PARAMS = dict(
    n_estimators=500,
    learning_rate=0.05,
    num_leaves=63,
    min_child_samples=20,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
)

_CALLBACKS = [
    lgb.early_stopping(stopping_rounds=50, verbose=False),
    lgb.log_evaluation(period=100),
]


def train_stage1(X_train, y_train, X_val, y_val):
    model = lgb.LGBMRegressor(**_BASE_PARAMS)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=_CALLBACKS)
    return model


def predict_stage1(model, X):
    return model.predict(X)



# Features fed to Stage 2 (per remaining hour, per plant):
#   - mean_recent_error   : mean(actual − s1_pred) over the last ≤6 elapsed hours
#   - std_recent_error    : std of recent errors (captures volatility)
#   - hour_of_day         : 0-23 of the hour being corrected
#   - physics_signal      : CMF (solar) or power_curve_fraction (wind) at that hour
#   - asset features      : capacity_mw, lat_sin, lat_cos, lon_sin, lon_cos

# Target: actual_error = actual_generation_mw − stage1_pred  (for that hour)
# At inference time, Stage 2 correction is added back to the Stage 1 forecast.

_STAGE2_FEATURES = [
    'mean_recent_error',
    'std_recent_error',
    'hour_of_day',
    # Physics signal: use whichever is non-null (solar vs wind asset)
    'CMF',
    'power_curve_fraction',
    # Asset identity (so Stage 2 also learns plant-specific bias patterns)
    'capacity_mw',
    'lat_sin',
    'lat_cos',
    'lon_sin',
    'lon_cos',
]


def build_stage2_training_data(df_with_s1_pred):
    """
    Build the Stage-2 training set from a DataFrame that already has:
        timestamp, plant_id, actual_generation_mw, s1_pred,
        CMF, power_curve_fraction, capacity_mw,
        lat_sin, lat_cos, lon_sin, lon_cos.

    For every (plant_id, date) pair, we simulate the intra-day setting:
    elapsed = hours 0..H-1,  target = hours H..23  for H in [1, 23].
    We compute residual features from elapsed hours and attach them to
    every remaining hour as the row the Stage-2 model will learn from.

    Returns X2 (DataFrame) and y2 (Series).
    """
    df = df_with_s1_pred.copy()
    df['date'] = df['timestamp'].dt.date
    df['hour_of_day'] = df['timestamp'].dt.hour
    df['error'] = df['actual_generation_mw'] - df['s1_pred']

    rows = []

    for (plant_id, date), day_df in df.groupby(['plant_id', 'date']):
        day_df = day_df.sort_values('hour_of_day').reset_index(drop=True)
        n = len(day_df)

        for split in range(1, n):                       # split = number of elapsed hours
            elapsed = day_df.iloc[:split]
            remaining = day_df.iloc[split:]

            # Residual summary from last ≤6 elapsed hours
            recent = elapsed.tail(6)['error'].values
            mean_err = float(np.mean(recent))
            std_err  = float(np.std(recent)) if len(recent) > 1 else 0.0

            for _, row in remaining.iterrows():
                rows.append({
                    'mean_recent_error':  mean_err,
                    'std_recent_error':   std_err,
                    'hour_of_day':        row['hour_of_day'],
                    'CMF':                row['CMF'],
                    'power_curve_fraction': row['power_curve_fraction'],
                    'capacity_mw':        row['capacity_mw'],
                    'lat_sin':            row['lat_sin'],
                    'lat_cos':            row['lat_cos'],
                    'lon_sin':            row['lon_sin'],
                    'lon_cos':            row['lon_cos'],
                    'target_error':       row['error'],
                })

    result = __import__('pandas').DataFrame(rows)
    X2 = result[_STAGE2_FEATURES]
    y2 = result['target_error']
    return X2, y2


def train_stage2(X2_train, y2_train, X2_val, y2_val):
    """Train the residual-correction model."""
    model = lgb.LGBMRegressor(**_BASE_PARAMS)
    model.fit(X2_train, y2_train, eval_set=[(X2_val, y2_val)], callbacks=_CALLBACKS)
    return model


def predict_stage2(stage2_model, mean_recent_error, std_recent_error,
                   hour_of_day, CMF, power_curve_fraction,
                   capacity_mw, lat_sin, lat_cos, lon_sin, lon_cos):
    """
    Predict the error correction for a single remaining hour/plant.
    Returns a scalar correction to add to the Stage-1 forecast.
    """
    import pandas as pd
    row = pd.DataFrame([{
        'mean_recent_error':    mean_recent_error,
        'std_recent_error':     std_recent_error,
        'hour_of_day':          hour_of_day,
        'CMF':                  CMF,
        'power_curve_fraction': power_curve_fraction,
        'capacity_mw':          capacity_mw,
        'lat_sin':              lat_sin,
        'lat_cos':              lat_cos,
        'lon_sin':              lon_sin,
        'lon_cos':              lon_cos,
    }])
    return float(stage2_model.predict(row)[0])


def intraday_update(stage1_model, stage2_model, day_df, cutoff_hour):
    """
    Simulate intra-day recalibration at `cutoff_hour` (0-23).

    day_df must contain for a single day, all plants:
        timestamp, plant_id, actual_generation_mw (for elapsed hours),
        and all Stage-1 feature columns.

    Returns a DataFrame with columns:
        plant_id, hour_of_day, s1_pred, correction, final_pred,
        actual (NaN for future hours).
    """
    import pandas as pd
    from feature_engineering import transform, FEATURE_COLS

    day_df = day_df.copy()
    day_df['hour_of_day'] = day_df['timestamp'].dt.hour

    results = []

    for plant_id, plant_df in day_df.groupby('plant_id'):
        plant_df = plant_df.sort_values('hour_of_day').reset_index(drop=True)

        # Stage 1 predictions for the full day
        X_day, _ = transform(plant_df)
        s1_preds = predict_stage1(stage1_model, X_day)
        plant_df['s1_pred'] = s1_preds

        elapsed  = plant_df[plant_df['hour_of_day'] < cutoff_hour]
        future   = plant_df[plant_df['hour_of_day'] >= cutoff_hour]

        # Residual summary from elapsed hours (last ≤6)
        if len(elapsed) > 0:
            recent_errs = (elapsed['actual_generation_mw'] - elapsed['s1_pred']).tail(6).values
            mean_err = float(np.mean(recent_errs))
            std_err  = float(np.std(recent_errs)) if len(recent_errs) > 1 else 0.0
        else:
            mean_err, std_err = 0.0, 0.0

        # Asset metadata (constant for this plant)
        meta = plant_df.iloc[0]

        for _, row in future.iterrows():
            correction = predict_stage2(
                stage2_model,
                mean_recent_error=mean_err,
                std_recent_error=std_err,
                hour_of_day=row['hour_of_day'],
                CMF=row['CMF'],
                power_curve_fraction=row['power_curve_fraction'],
                capacity_mw=meta['capacity_mw'],
                lat_sin=meta['lat_sin'],
                lat_cos=meta['lat_cos'],
                lon_sin=meta['lon_sin'],
                lon_cos=meta['lon_cos'],
            )
            results.append({
                'plant_id':   plant_id,
                'hour_of_day': row['hour_of_day'],
                's1_pred':    row['s1_pred'],
                'correction': correction,
                'final_pred': row['s1_pred'] + correction,
                'actual':     row.get('actual_generation_mw', float('nan')),
            })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def save_model(model, path):
    joblib.dump(model, path)


def load_model(path):
    return joblib.load(path)


# Keep the Day-2 alias so main.py import doesn't break
train  = train_stage1
predict = predict_stage1