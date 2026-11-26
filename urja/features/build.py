"""L2: build the day-ahead table. One row = one plant-hour.

LEAKAGE RULE (tested in tests/test_invariants.py): every feature is computed from the forecasts
available at filing time, solar geometry or the calendar. Nothing from the truth source (ERA5 or
Elia's measurements) may enter a feature column. Truth only produces the target `y` (output / capacity).
Site lat/lon are NOT features in v3, so the model can be applied to sites it has never seen.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from urja import config as C
from urja.data.elia import fetch_elia
from urja.data.fetch import fetch_truth
from urja.data.lead import filed_forecast
from urja.physics.power import solar_geometry, to_mw

TARGET = "y"
ELIA_COLS = ["elia_p10", "elia_p50", "elia_p90"]
META = ["time", "plant_id", "kind", "split", "actual_mw", TARGET, "daylight", "capacity_mw"] + ELIA_COLS


def _truth(site: C.Site, geom_for) -> tuple[pd.DatetimeIndex, pd.Series, pd.Series, pd.DataFrame | None]:
    """(index, actual MW, capacity MW, Elia baseline as capacity fractions or None)."""
    if site.truth == "elia":
        e = fetch_elia(site)
        e = e[e["capacity"] > 0]
        base = e[["elia_p10", "elia_p50", "elia_p90"]].div(e["capacity"], axis=0)
        return e.index, e["measured"].clip(lower=0), e["capacity"], base
    t = fetch_truth(site)
    return t.index, to_mw(t, site, geom_for(t.index)), pd.Series(site.ac_mw, index=t.index), None


def _site_table(site: C.Site) -> pd.DataFrame:
    idx, actual, capacity, elia = _truth(site, lambda i: solar_geometry(i, site))
    geom = solar_geometry(idx, site)
    cap = site.ac_mw
    f = pd.DataFrame(index=idx)

    phys = []
    for m in C.NWP_MODELS:
        fc, run_day = filed_forecast(site, m, idx)
        tag = m.split("_")[0]
        p = to_mw(fc, site, geom) / cap
        driver = "shortwave_radiation" if site.kind == "solar" else "wind_speed_100m"
        p[fc[driver].isna().to_numpy()] = np.nan    # a missing forecast is unknown, never "0 MW"
        f[f"phys_{tag}"] = p.to_numpy()
        f[f"ghi_{tag}"] = fc["shortwave_radiation"].to_numpy()
        f[f"ws_{tag}"] = fc["wind_speed_100m"].to_numpy()
        f[f"cloud_{tag}"] = fc["cloud_cover"].to_numpy()
        f[f"temp_{tag}"] = fc["temperature_2m"].to_numpy()
        phys.append(p.to_numpy())
    P = np.vstack(phys)
    f["phys_mean"] = np.nanmean(P, 0)              # a missing model hour (rare, ICON) is skipped
    f["phys_std"] = np.nanstd(P, 0)                # model disagreement, in capacity units
    f["phys_range"] = np.nanmax(P, 0) - np.nanmin(P, 0)
    ghi_cols = [c for c in f if c.startswith("ghi_")]
    ws_cols = [c for c in f if c.startswith("ws_")]
    f["ghi_mean"] = f[ghi_cols].mean(1)
    f["ws_mean"] = f[ws_cols].mean(1)
    f["ws_std"] = f[ws_cols].std(1)
    f["cloud_mean"] = f[[c for c in f if c.startswith("cloud_")]].mean(1)
    f["cloud_std"] = f[[c for c in f if c.startswith("cloud_")]].std(1)
    f["clearsky_ghi"] = geom["clearsky_ghi"].to_numpy()
    f["zenith"] = geom["zenith"].to_numpy()
    f["kt_fc"] = np.where(f["clearsky_ghi"] > 20, f["ghi_mean"] / f["clearsky_ghi"].clip(lower=20), 0.0)

    # Physical ceiling: what the plant would make under a perfectly clear sky (solar only).
    if site.kind == "solar":
        cs_weather = pd.DataFrame({"shortwave_radiation": geom["clearsky_ghi"],
                                   "temperature_2m": f["temp_ecmwf"]}, index=idx)
        f["ceiling"] = (to_mw(cs_weather, site, geom) / cap).to_numpy()
    else:
        f["ceiling"] = 0.92

    # Same-day context from the same day-ahead run (still forecast-only).
    day = idx.normalize()
    f["day_ghi_fc"] = f.groupby(day)["ghi_mean"].transform("sum").to_numpy() / 1000.0
    f["day_cloud_fc"] = f.groupby(day)["cloud_mean"].transform("mean").to_numpy()
    f["day_ws_fc"] = f.groupby(day)["ws_mean"].transform("mean").to_numpy()

    h, d = idx.hour, idx.dayofyear
    f["hour_sin"], f["hour_cos"] = np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24)
    f["doy_sin"], f["doy_cos"] = np.sin(2 * np.pi * d / 365.25), np.cos(2 * np.pi * d / 365.25)
    f["lat"], f["lon"] = site.lat, site.lon
    f["lead_day"] = run_day                         # 1 or 2: known at filing time

    f["actual_mw"] = actual.to_numpy()
    f["capacity_mw"] = capacity.to_numpy()
    f[TARGET] = (actual / capacity).clip(0, 1).to_numpy()
    for c in ELIA_COLS:
        f[c] = elia[c].clip(0, 1).to_numpy() if elia is not None else np.nan
    f["daylight"] = (f["zenith"] < 90) if site.kind == "solar" else True
    f["plant_id"], f["kind"] = site.plant_id, site.kind
    f = f.reset_index().rename(columns={"index": "time"})
    return f


def assign_split(t: pd.Series) -> pd.Series:
    t = pd.to_datetime(t)
    test = t >= pd.Timestamp(C.TEST_START, tz=C.TZ)
    val = (~test) & (t >= pd.Timestamp(C.VAL_START, tz=C.TZ))
    week = t.dt.isocalendar().week.astype(int)
    calib = (~test) & (~val) & (week % C.CALIB_EVERY_NTH_WEEK == 0)
    return pd.Series(np.select([test, val, calib], ["test", "val", "calib"], "train"), index=t.index)


def build_table(sites=C.SITES, name: str = "table") -> pd.DataFrame:
    path = C.ART_DIR / f"{name}_{C.LEAD_MODE}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    df = pd.concat([_site_table(s) for s in sites], ignore_index=True)
    df["split"] = assign_split(df["time"])
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def feature_columns(df: pd.DataFrame, drop: tuple[str, ...] = ()) -> list[str]:
    cols = [c for c in df.columns if c not in META and c not in ("kind", "lat", "lon")]
    return [c for c in cols if not any(c.startswith(p) for p in drop)]
