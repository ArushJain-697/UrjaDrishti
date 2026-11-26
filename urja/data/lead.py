"""Which forecast could the scheduler actually have used?

A schedule for local day D is filed at `site.filing_hour` (in `site.filing_tz`) on day D-1. A model run
initialised at time I is usable only if I + PUBLISH_LATENCY_H <= that deadline. Open-Meteo's
`previous_dayN` value for hour t comes from the run initialised ~N x 24 h before t, rounded down to
the 6-hourly cycle. For each hour we take the smallest N whose run was usable.

Watch-out: do the arithmetic in UTC. The deadline is local; the model cycles are UTC.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from urja import config as C
from urja.data.fetch import fetch_forecast

MAX_DAY = 2


def filing_deadline_utc(times: pd.DatetimeIndex, site: C.Site) -> pd.DatetimeIndex:
    local_day = times.tz_convert(site.filing_tz).normalize()
    deadline = (local_day - pd.Timedelta(days=1)).tz_localize(None) + pd.Timedelta(hours=site.filing_hour)
    return deadline.tz_localize(site.filing_tz, ambiguous="NaT", nonexistent="shift_forward").tz_convert("UTC")


def run_day_needed(times: pd.DatetimeIndex, site: C.Site) -> np.ndarray:
    """For each target hour, the smallest N (1..MAX_DAY) whose previous_dayN run was published by the deadline."""
    t_utc = times.tz_convert("UTC")
    deadline = filing_deadline_utc(times, site)
    need = np.full(len(times), MAX_DAY + 1)
    for n in range(MAX_DAY, 0, -1):
        init = (t_utc - pd.Timedelta(days=n)).floor(f"{C.RUN_EVERY_H}h")
        ok = (init + pd.Timedelta(hours=C.PUBLISH_LATENCY_H)) <= deadline
        need = np.where(ok, n, need)
    return need


def filed_forecast(site: C.Site, model: str, index: pd.DatetimeIndex) -> tuple[pd.DataFrame, np.ndarray]:
    """The forecast available at filing time for every hour in `index`, and which run-day it came from."""
    if C.LEAD_MODE == "day1":
        return fetch_forecast(site, model, 1).reindex(index), np.ones(len(index), int)
    n = run_day_needed(index, site)
    if (n > MAX_DAY).any():
        raise ValueError(f"{site.plant_id}: some hours need a run older than previous_day{MAX_DAY}")
    d1 = fetch_forecast(site, model, 1).reindex(index)
    d2 = fetch_forecast(site, model, 2).reindex(index)
    out = d1.where(pd.DataFrame(np.repeat((n == 1)[:, None], d1.shape[1], 1), index=d1.index, columns=d1.columns), d2)
    return out, n
