"""L0: fetch real weather. Two sources, never mixed:

* truth    -- ERA5 reanalysis (Open-Meteo archive API): what the weather actually was.
* forecast -- archived day-ahead runs of ECMWF IFS, GFS and ICON (Open-Meteo previous-runs API):
              what each model said ~24 h earlier. This is the ONLY weather the model may see.

Both are hourly, local time (Asia/Kolkata). Radiation is the mean over the *preceding* hour.
Results are cached as parquet under data/raw/ so re-runs are offline.
"""
from __future__ import annotations

import time

import pandas as pd
import requests

from urja import config as C

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"


def _get(url: str, params: dict, tries: int = 4) -> dict:
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=120)
            if r.status_code == 429:
                time.sleep(20 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"rate-limited too many times: {url}")


def _frame(payload: dict) -> pd.DataFrame:
    h = payload["hourly"]
    df = pd.DataFrame(h)
    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(C.TZ)
    return df.set_index("time")


def fetch_truth(site: C.Site) -> pd.DataFrame:
    path = C.RAW_DIR / f"truth_{site.plant_id}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    p = dict(latitude=site.lat, longitude=site.lon, start_date=C.PERIOD_START, end_date=C.PERIOD_END,
             hourly=",".join(C.TRUTH_VARS), timezone=C.TZ, wind_speed_unit="ms", models="era5")
    df = _frame(_get(ARCHIVE_URL, p))
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def fetch_forecast(site: C.Site, model: str) -> pd.DataFrame:
    """Day-ahead forecast for every hour, columns named <var> (suffix stripped)."""
    path = C.RAW_DIR / f"fc_{site.plant_id}_{model}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    vars_ = ",".join(v + C.LEAD_SUFFIX for v in C.NWP_VARS)
    p = dict(latitude=site.lat, longitude=site.lon, start_date=C.PERIOD_START, end_date=C.PERIOD_END,
             hourly=vars_, timezone=C.TZ, wind_speed_unit="ms", models=model)
    df = _frame(_get(PREVIOUS_RUNS_URL, p))
    df.columns = [c.removesuffix(C.LEAD_SUFFIX) for c in df.columns]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def fetch_all() -> None:
    for s in C.SITES:
        fetch_truth(s)
        for m in C.NWP_MODELS:
            fetch_forecast(s, m)
            time.sleep(1)


if __name__ == "__main__":
    fetch_all()
    for f in sorted(C.RAW_DIR.glob("*.parquet")):
        d = pd.read_parquet(f)
        print(f"{f.name:32s} rows={len(d):6d} first_valid={d.dropna().index.min()} nan%={d.isna().mean().mean():.3f}")
