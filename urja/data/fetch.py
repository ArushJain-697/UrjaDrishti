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


def _frame(payload: dict, tz: str) -> pd.DataFrame:
    """Payload is always requested in UTC, then converted. Asking Open-Meteo for Asia/Kolkata
    shifts the data by a whole 5 h and labels it as +5:30, putting every row 30 min early
    (found in v3 via the NASA cross-check; BUILD_LOG #11)."""
    h = payload["hourly"]
    df = pd.DataFrame(h)
    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize("UTC").dt.tz_convert(tz)
    return df.set_index("time")


def fetch_truth(site: C.Site) -> pd.DataFrame:
    path = C.RAW_DIR / f"truth_{site.plant_id}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    p = dict(latitude=site.lat, longitude=site.lon, start_date=C.PERIOD_START, end_date=C.PERIOD_END,
             hourly=",".join(C.TRUTH_VARS), timezone="UTC", wind_speed_unit="ms", models="era5")
    df = _frame(_get(ARCHIVE_URL, p), site.tz)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def fetch_forecast(site: C.Site, model: str, day: int = 1) -> pd.DataFrame:
    """Forecast from the run ~`day` x 24 h before each hour, columns named <var> (suffix stripped)."""
    tag = "" if day == 1 else f"_d{day}"
    path = C.RAW_DIR / f"fc_{site.plant_id}_{model}{tag}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    suffix = f"_previous_day{day}"
    vars_ = ",".join(v + suffix for v in C.NWP_VARS)
    p = dict(latitude=site.lat, longitude=site.lon, start_date=C.PERIOD_START, end_date=C.PERIOD_END,
             hourly=vars_, timezone="UTC", wind_speed_unit="ms", models=model)
    df = _frame(_get(PREVIOUS_RUNS_URL, p), site.tz)
    df.columns = [c.removesuffix(suffix) for c in df.columns]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def fetch_all(sites=C.SITES, truth: bool = True) -> None:
    for s in sites:
        if truth and s.truth == "physics":
            fetch_truth(s)
        for m in C.NWP_MODELS:
            for day in (1, 2):
                fetch_forecast(s, m, day)
                time.sleep(1)


if __name__ == "__main__":
    fetch_all()
    for f in sorted(C.RAW_DIR.glob("*.parquet")):
        d = pd.read_parquet(f)
        print(f"{f.name:32s} rows={len(d):6d} first_valid={d.dropna().index.min()} nan%={d.isna().mean().mean():.3f}")
