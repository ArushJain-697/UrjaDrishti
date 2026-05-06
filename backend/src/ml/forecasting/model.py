import logging
import warnings
import numpy as np
import pandas as pd
import lightgbm as lgb
import joblib

logging.getLogger().setLevel(logging.WARNING)
logging.getLogger('mapie').setLevel(logging.WARNING)
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.WARNING)
logging.disable(logging.INFO)    
warnings.filterwarnings('ignore', category=UserWarning)  

from mapie.regression import ConformalizedQuantileRegressor

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

_QUANTILE_PARAMS = dict(
    n_estimators=500,
    learning_rate=0.05,
    num_leaves=63,
    min_child_samples=20,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    objective='quantile',
)

_CALLBACKS = [
    lgb.early_stopping(stopping_rounds=50, verbose=False),
    lgb.log_evaluation(period=200),
]


def _augment_cutout_events(X_train, y_train, multiplier=15):
    if 'above_cutout' not in X_train.columns:
        return X_train, y_train
    mask = X_train['above_cutout'] == 1
    if mask.sum() == 0:
        return X_train, y_train
    X_co = pd.concat([X_train[mask]] * multiplier, ignore_index=True)
    y_co = pd.concat([y_train[mask]] * multiplier, ignore_index=True)
    X_aug = pd.concat([X_train, X_co], ignore_index=True)
    y_aug = pd.concat([y_train, y_co], ignore_index=True)
    return (
        X_aug.sample(frac=1, random_state=42).reset_index(drop=True),
        y_aug.sample(frac=1, random_state=42).reset_index(drop=True),
    )


def train_stage1(X_train, y_train, X_calib, y_calib, X_val, y_val):
    X_train, y_train = _augment_cutout_events(X_train, y_train, multiplier=15)

    def _fit_quantile(alpha_q, label):
        print(f"[Stage-1] Training {label} quantile model (alpha={alpha_q}) ...")
        m = lgb.LGBMRegressor(**_QUANTILE_PARAMS, alpha=alpha_q)
        m.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=_CALLBACKS)
        return m

    m_p10 = _fit_quantile(0.1, "P10")
    m_p50 = _fit_quantile(0.5, "P50")
    m_p90 = _fit_quantile(0.9, "P90")

    print("[Stage-1] Calibrating prediction intervals with MAPIE ...")
    cqr = ConformalizedQuantileRegressor(
        estimator=[m_p10, m_p50, m_p90],
        confidence_level=0.85,
        prefit=True,
    )
    cqr.conformalize(X_calib, y_calib)
    return cqr


def _predict_interval_clipped(cqr_model, X):
    p50, pis = cqr_model.predict_interval(X)
    p10_raw = pis[:, 0, 0]
    p90_raw = pis[:, 1, 0]

    p10 = np.minimum(p10_raw, p50)
    p90 = np.maximum(p90_raw, p50)

    if isinstance(X, pd.DataFrame) and 'above_cutout' in X.columns:
        cutout_mask = X['above_cutout'].values > 0
        if cutout_mask.any():
            cap_proxy = X['capacity_mw'].values if 'capacity_mw' in X.columns else np.ones(len(X))
            p50 = np.where(cutout_mask, 0.0, p50)
            p10 = np.where(cutout_mask, 0.0, p10)
            p90 = np.where(cutout_mask, cap_proxy * 0.05, p90)

    return p50, p10, p90


def predict_stage1(cqr_model, X, return_pis=False):
    if return_pis:
        return _predict_interval_clipped(cqr_model, X)
    p50, _, _ = _predict_interval_clipped(cqr_model, X)
    return p50


_STAGE2_FEATURES = [
    'mean_recent_error',
    'std_recent_error',
    'hour_of_day',
    'CMF',
    'power_curve_fraction',
    'capacity_mw',
    'lat_sin',
    'lat_cos',
    'lon_sin',
    'lon_cos',
]


def build_stage2_training_data(df_with_s1_pred):
    df = df_with_s1_pred.copy()
    df['date']        = df['timestamp'].dt.date
    df['hour_of_day'] = df['timestamp'].dt.hour
    df['error']       = df['actual_generation_mw'] - df['s1_pred']

    rows = []

    for (plant_id, date), day_df in df.groupby(['plant_id', 'date']):
        day_df = day_df.sort_values('hour_of_day').reset_index(drop=True)
        n = len(day_df)

        for split in range(1, n):
            elapsed   = day_df.iloc[:split]
            remaining = day_df.iloc[split:]

            recent   = elapsed.tail(6)['error'].values
            mean_err = float(np.mean(recent))
            std_err  = float(np.std(recent)) if len(recent) > 1 else 0.0

            for _, row in remaining.iterrows():
                rows.append({
                    'mean_recent_error':    mean_err,
                    'std_recent_error':     std_err,
                    'hour_of_day':          row['hour_of_day'],
                    'CMF':                  row['CMF'],
                    'power_curve_fraction': row['power_curve_fraction'],
                    'capacity_mw':          row['capacity_mw'],
                    'lat_sin':              row['lat_sin'],
                    'lat_cos':              row['lat_cos'],
                    'lon_sin':              row['lon_sin'],
                    'lon_cos':              row['lon_cos'],
                    'target_error':         row['error'],
                })

    result = pd.DataFrame(rows)
    X2 = result[_STAGE2_FEATURES]
    y2 = result['target_error']
    return X2, y2


def train_stage2(X2_train, y2_train, X2_val, y2_val):
    model = lgb.LGBMRegressor(**_BASE_PARAMS)
    model.fit(
        X2_train, y2_train,
        eval_set=[(X2_val, y2_val)],
        callbacks=_CALLBACKS,
    )
    return model


def predict_stage2(stage2_model, mean_recent_error, std_recent_error,
                   hour_of_day, CMF, power_curve_fraction,
                   capacity_mw, lat_sin, lat_cos, lon_sin, lon_cos):
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
    from feature_engineering import transform

    day_df = day_df.copy()
    day_df['hour_of_day'] = day_df['timestamp'].dt.hour

    results = []

    for plant_id, plant_df in day_df.groupby('plant_id'):
        plant_df = plant_df.sort_values('hour_of_day').reset_index(drop=True)

        X_day, _ = transform(plant_df)
        s1_preds, p10_arr, p90_arr = predict_stage1(stage1_model, X_day, return_pis=True)
        plant_df['s1_pred'] = s1_preds
        plant_df['p10']     = p10_arr
        plant_df['p90']     = p90_arr

        elapsed = plant_df[plant_df['hour_of_day'] < cutoff_hour]
        future  = plant_df[plant_df['hour_of_day'] >= cutoff_hour]

        if len(elapsed) > 0:
            recent_errs = (elapsed['actual_generation_mw'] - elapsed['s1_pred']).tail(6).values
            mean_err = float(np.mean(recent_errs))
            std_err  = float(np.std(recent_errs)) if len(recent_errs) > 1 else 0.0
        else:
            mean_err, std_err = 0.0, 0.0

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
                'plant_id':    plant_id,
                'hour_of_day': row['hour_of_day'],
                's1_pred':     row['s1_pred'],
                'p10':         row['p10'],
                'p90':         row['p90'],
                'correction':  correction,
                'final_pred':  row['s1_pred'] + correction,
                'final_p10':   row['p10']     + correction,
                'final_p90':   row['p90']     + correction,
                'actual':      row.get('actual_generation_mw', float('nan')),
            })

    return pd.DataFrame(results)


def get_forecast(stage1_model, stage2_model, current_features_df, recent_actuals_df=None):
    from feature_engineering import transform, FEATURE_COLS as _FC

    df = current_features_df.copy()
    df['hour_of_day'] = pd.to_datetime(df['timestamp']).dt.hour

    X, _ = transform(df)
    p50, p10, p90 = predict_stage1(stage1_model, X, return_pis=True)

    df['p50'] = p50
    df['p10'] = p10
    df['p90'] = p90

    if stage2_model is not None and recent_actuals_df is not None:
        ra = recent_actuals_df.copy()
        ra['timestamp'] = pd.to_datetime(ra['timestamp'])

        if all(c in ra.columns for c in _FC):
            X_elapsed, _ = transform(ra)
            ra['s1_pred'] = predict_stage1(stage1_model, X_elapsed)
            ra['error']   = ra['actual_generation_mw'] - ra['s1_pred']
        else:
            ra['error'] = 0.0

        def _summary(grp):
            recent = grp.sort_values('timestamp').tail(6)['error'].values
            return pd.Series({
                'mean_recent_error': float(np.mean(recent)),
                'std_recent_error':  float(np.std(recent)) if len(recent) > 1 else 0.0,
            })

        plant_summary = ra.groupby('plant_id').apply(_summary)

        corrections = np.zeros(len(df))
        for i, row in df.iterrows():
            pid = row['plant_id']
            if pid not in plant_summary.index:
                continue
            corr = predict_stage2(
                stage2_model,
                mean_recent_error=plant_summary.loc[pid, 'mean_recent_error'],
                std_recent_error=plant_summary.loc[pid, 'std_recent_error'],
                hour_of_day=row['hour_of_day'],
                CMF=row.get('CMF', 0.0),
                power_curve_fraction=row.get('power_curve_fraction', 0.0),
                capacity_mw=row.get('capacity_mw', 1.0),
                lat_sin=row.get('lat_sin', 0.0),
                lat_cos=row.get('lat_cos', 1.0),
                lon_sin=row.get('lon_sin', 0.0),
                lon_cos=row.get('lon_cos', 1.0),
            )
            corrections[i] = corr

        df['p50'] += corrections
        df['p10'] += corrections
        df['p90'] += corrections

    return df[['plant_id', 'hour_of_day', 'p50', 'p10', 'p90']].rename(
        columns={'hour_of_day': 'hour'}
    )


def save_model(model, path):
    joblib.dump(model, path)


def load_model(path):
    return joblib.load(path)


train   = train_stage1
predict = predict_stage1