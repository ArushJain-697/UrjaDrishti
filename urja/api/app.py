"""Read-only API over the replay predictions and the metrics JSON. No model runs per request.

    uvicorn urja.api.app:app --port 8000
"""
from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from urja import config as C

app = FastAPI(title="UrjaDrishti", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def _test_unsealed() -> bool:
    return (C.RESULTS_DIR / "metrics_test.json").exists()


@lru_cache(maxsize=1)
def _replay() -> pd.DataFrame:
    path = C.ART_DIR / "replay.parquet"
    if not path.exists():
        raise HTTPException(503, "Run `python -m urja.train` first.")
    return pd.read_parquet(path)


def _visible() -> pd.DataFrame:
    r = _replay()
    allowed = ["val", "test"] if _test_unsealed() else ["val"]
    return r[r["split"].isin(allowed)]


@app.get("/api/sites")
def sites():
    return [{"plant_id": s.plant_id, "name": s.name, "kind": s.kind, "lat": s.lat, "lon": s.lon,
             "ac_mw": s.ac_mw} for s in C.SITES]


@app.get("/api/days")
def days():
    v = _visible()
    d = v.groupby(v["time"].dt.strftime("%Y-%m-%d")).agg(red=("review_required", "sum"), split=("split", "first"))
    return [{"date": k, "red_hours": int(r.red), "split": r.split} for k, r in d.iterrows()]


@app.get("/api/day/{date}")
def day(date: str):
    v = _visible()
    d = v[v["time"].dt.strftime("%Y-%m-%d") == date]
    if d.empty:
        raise HTTPException(404, "No visible data for that date (the test year stays sealed until scored).")
    out = {}
    for pid, g in d.groupby("plant_id"):
        g = g.sort_values("time")
        dev = (g["actual_mw"] - g["schedule_mw"]).abs()
        band = C.DSM_FREE_BAND * C.SITE_BY_ID[pid].ac_mw
        out[pid] = {
            "hours": g["time"].dt.hour.tolist(),
            "p10": g["p10_mw"].tolist(), "p50": g["schedule_mw"].tolist(), "p90": g["p90_mw"].tolist(),
            "actual": g["actual_mw"].tolist(), "tier": g["tier"].tolist(),
            "nwp": {m: g[f"phys_{m}"].tolist() for m in ("ecmwf", "gfs", "icon")},
            "review_hours": g.loc[g["review_required"], "time"].dt.hour.tolist(),
            "excess_mwh": float((dev - band).clip(lower=0).sum()),
            "free_band_mw": band,
        }
    return {"date": date, "split": d["split"].iloc[0], "plants": out}


@app.get("/api/metrics")
def metrics():
    res = {}
    for name in ("val", "test"):
        p = C.RESULTS_DIR / f"metrics_{name}.json"
        if p.exists():
            res[name] = json.loads(p.read_text())
    res["edge"] = {p.stem.removeprefix("edge_"): json.loads(p.read_text()) for p in C.RESULTS_DIR.glob("edge_*.json")}
    return res


_dist = C.ROOT / "web" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")
