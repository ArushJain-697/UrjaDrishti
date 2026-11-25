"""L2: build the day-ahead table. One row = one plant-hour.

LEAKAGE RULE (tested in tests/test_leakage.py): every feature is computed from the
day-ahead NWP forecasts, solar geometry or the calendar. Nothing from the truth source
(ERA5) may enter a feature column. Truth only produces the target `y` (generation / capacity).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from urja import config as C
from urja.data.fetch import fetch_forecast, fetch_truth
from urja.physics.power import solar_geometry, to_mw

TARGET = "y"
META = ["time", "plant_id", "kind", "split", "actual_mw", TARGET, "daylight"]


def _site_table(site: C.Site) -> pd.DataFrame:
    truth = fetch_truth(site)
    idx = truth.index
    geom = solar_geometry(idx, site)
    cap = site.ac_mw
    f = pd.DataFrame(index=idx)

    phys = []
    for m in C.NWP_MODELS:
        fc = fetch_forecast(site, m).reindex(idx)
        tag = m.split("_")[0]
        p = to_mw(fc, site, geom) / cap
        f[f"phys_{tag}"] = p.to_numpy()
        f[f"ghi_{tag}"] = fc["shortwave_radiation"].to_numpy()
        f[f"ws_{tag}"] = fc["wind_speed_100m"].to_numpy()
        f[f"cloud_{tag}"] = fc["cloud_cover"].to_numpy()
        f[f"temp_{tag}"] = fc["temperature_2m"].to_numpy()
        phys.append(p.to_numpy())
    P = np.vstack(phys)
    f["phys_mean"] = P.mean(0)
    f["phys_std"] = P.std(0)                       # model disagreement, in capacity units
    f["phys_range"] = P.max(0) - P.min(0)
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

    actual = to_mw(truth, site, geom)
    f["actual_mw"] = actual.to_numpy()
    f[TARGET] = f["actual_mw"] / cap
    f["daylight"] = (f["zenith"] < 90) if site.kind == "solar" else True
    f["plant_id"], f["kind"] = site.plant_id, site.kind
    f = f.reset_index().rename(columns={"index": "time"})
    return f


def assign_split(t: pd.Series) -> pd.Series:
    t = pd.to_datetime(t)
    held = t >= pd.Timestamp(C.HELDOUT_START, tz=C.TZ)
    week = t.dt.isocalendar().week.astype(int)
    calib = (~held) & (week % C.CALIB_EVERY_NTH_WEEK == 0)
    return pd.Series(np.select([held, calib], ["heldout", "calib"], "train"), index=t.index)


def build_table() -> pd.DataFrame:
    path = C.ART_DIR / "table.parquet"
    if path.exists():
        return pd.read_parquet(path)
    df = pd.concat([_site_table(s) for s in C.SITES], ignore_index=True)
    df["split"] = assign_split(df["time"])
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def feature_columns(df: pd.DataFrame, drop: tuple[str, ...] = ()) -> list[str]:
    cols = [c for c in df.columns if c not in META and c not in ("kind",)]
    return [c for c in cols if not any(c.startswith(p) for p in drop)]
