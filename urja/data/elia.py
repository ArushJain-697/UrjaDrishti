"""Measured generation and Elia's own day-ahead forecast (Belgian TSO open data, opendata.elia.be).

Returned hourly in UTC, aligned to Open-Meteo's convention: the row stamped t holds the mean over the
PRECEDING hour (t-1h, t]. Elia stamps 15-minute intervals by their START, so the four quarters
starting at 09:00, 09:15, 09:30, 09:45 average into the row stamped 10:00.

Columns (MW): measured, capacity (monitored), elia_p50 / elia_p10 / elia_p90 (dayahead11h: issued 11:00
Brussels on the day before, the same deadline our model is held to).
"""
from __future__ import annotations

import io

import pandas as pd
import requests

from urja import config as C

EXPORT = "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/{ds}/exports/csv"
FIELDS = {"measured": "measured", "monitoredcapacity": "capacity", "dayahead11hforecast": "elia_p50",
          "dayahead11hconfidence10": "elia_p10", "dayahead11hconfidence90": "elia_p90"}


def fetch_elia(site: C.Site) -> pd.DataFrame:
    path = C.RAW_DIR / f"elia_{site.plant_id}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    ds, region = site.elia_series.split(":")
    where = (f'region="{region}" and datetime>="{C.PERIOD_START}T00:00:00" '
             f'and datetime<"{pd.Timestamp(C.PERIOD_END) + pd.Timedelta(days=1):%Y-%m-%d}T01:00:00"')
    if ds == "ods031":
        where += ' and offshoreonshore="Offshore"'
    r = requests.get(EXPORT.format(ds=ds), params={"where": where, "select": "datetime," + ",".join(FIELDS),
                                                   "delimiter": ",", "timezone": "UTC"}, timeout=600)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    # Several grid-connection rows can share a timestamp (wind): sum MW, then align to hour-ending.
    df = df.groupby("datetime")[list(FIELDS)].sum(min_count=1).rename(columns=FIELDS)
    hourly = df.resample("1h", label="right", closed="left").mean()
    hourly = hourly[hourly.index.minute == 0]
    hourly.index.name = "time"
    path.parent.mkdir(parents=True, exist_ok=True)
    hourly.to_parquet(path)
    return hourly
