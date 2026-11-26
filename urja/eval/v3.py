"""v3 evaluation. Every v3 number in the README comes from the JSON this writes.

    python -m urja.eval.v3            # dev report  -> results/v3_dev.json
    python -m urja.eval.v3 --final    # SEALED slices, once -> results/v3_sealed.json

Dev report
  lead          v2's ~24 h lead vs the real filing-deadline lead (24-48 h), Karnataka dev sites
  second_truth  solar skill scored against ERA5 (ECMWF family) and NASA POWER (satellite)
  elia_dev      measured Belgian output, our model vs Elia's own day-ahead P10/P50/P90 (dev period)
Sealed (docs/V3_SEAL.md)
  spatial       4 Karnataka sites never seen, Apr 2025 - Oct 2026 (after the training year)
  elia_test     Belgian measured output, Nov 2025 - Oct 2026
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from urja import config as C
from urja.eval import metrics as M
from urja.eval import run as R
from urja.features.build import build_table, feature_columns
from urja.models.common import LEVELS
from urja.models.quantile import QuantileForecaster

Q3 = (0.1, 0.5, 0.9)
NWP = ["phys_ecmwf", "phys_gfs", "phys_icon"]


def _q3(q9: np.ndarray) -> np.ndarray:
    return q9[:, [0, 4, 8]]


def _mos(train: pd.DataFrame, d: pd.DataFrame) -> np.ndarray:
    X = lambda x: x[NWP].apply(lambda c: c.fillna(x["phys_mean"])).fillna(0)
    return np.clip(Ridge(alpha=1.0).fit(X(train), train["y"]).predict(X(d)), 0, 1)


def _forecasters(df: pd.DataFrame) -> dict:
    cols = feature_columns(df)
    return {k: QuantileForecaster(k, cols).fit(df).calibrate(df) for k in sorted(df["kind"].unique())}


def _score(d: pd.DataFrame, f: QuantileForecaster, train: pd.DataFrame, with_elia: bool) -> dict:
    y = d["y"].to_numpy()
    p = f.predict(d)
    q9 = p[[c for c in p.columns if c.startswith("q")]].to_numpy()
    out = {"n_hours": int(len(d)), "blend_w": f.w_ens, "blend_anchor": f.anchor,
           "model": {"nmae": M.nmae(y, p["p50"]), "crps9": M.crps_from_quantiles(y, q9, LEVELS),
                     "qs3": M.crps_from_quantiles(y, np.column_stack([p["p10"], p["p50"], p["p90"]]), Q3),
                     "coverage_80": M.coverage(y, p["p10"], p["p90"]), "width_80": M.width(p["p10"], p["p90"]),
                     "dsm_excess": M.dsm_excess(y, p["p50"]),
                     "red_coverage": M.coverage(y[p["tier"] == "RED"], p["p10"][p["tier"] == "RED"], p["p90"][p["tier"] == "RED"]),
                     "red_share_hours": float((p["tier"] == "RED").mean())},
           "nwp_ensemble": {"nmae": M.nmae(y, d["phys_mean"].fillna(0)), "dsm_excess": M.dsm_excess(y, d["phys_mean"].fillna(0))},
           "linear_mos": {"nmae": M.nmae(y, _mos(train, d))}}
    for c in NWP:
        out["nwp_" + c.split("_")[1]] = {"nmae": M.nmae(y, d[c].fillna(d["phys_mean"]).fillna(0))}
    if with_elia:
        e = d[["elia_p10", "elia_p50", "elia_p90"]].to_numpy()
        out["elia_dayahead"] = {"nmae": M.nmae(y, e[:, 1]), "qs3": M.crps_from_quantiles(y, e, Q3),
                                "coverage_80": M.coverage(y, e[:, 0], e[:, 2]), "width_80": M.width(e[:, 0], e[:, 2]),
                                "dsm_excess": M.dsm_excess(y, e[:, 1])}
    return out


def _rows(df, kind, splits):
    d = df[(df["kind"] == kind) & df["split"].isin(splits)]
    d = d[d["daylight"]] if kind == "solar" else d
    return d.dropna(subset=["phys_mean"])


# ---------------------------------------------------------------- dev
def lead_report() -> dict:
    out = {}
    for mode in ("day1", "filed"):
        code = ("import json;from urja.eval import run as R;r={s:R.run(s) for s in ('val','test')};"
                "print(json.dumps({s:{k:{'nmae':v['model']['nmae'],'crps':v['model']['crps'],'coverage_80':v['model']['coverage_80'],"
                "'dsm_excess':v['model']['dsm_excess'],'best_baseline':v['best_baseline'],'best_nmae':v['baselines'][v['best_baseline']]['nmae']}"
                " for k,v in r[s]['kinds'].items()} for s in r}))")
        env = dict(os.environ, URJA_LEAD=mode, PYTHONPATH=str(C.ROOT))
        res = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
        out[mode] = json.loads(res.stdout.strip().splitlines()[-1])
    return out


def second_truth() -> dict:
    from urja.data.nasa import fetch_nasa
    from urja.physics.power import solar_geometry, to_mw
    df = build_table()
    f = _forecasters(df)["solar"]
    res = {}
    for site in [s for s in C.SITES if s.kind == "solar"]:
        d = _rows(df, "solar", ("val", "test"))
        d = d[d["plant_id"] == site.plant_id].copy()
        n = fetch_nasa(site).tz_convert(site.tz).reindex(pd.DatetimeIndex(d["time"]))
        ok = n["shortwave_radiation"].notna().to_numpy()
        d, n = d[ok], n[ok]
        d["y_nasa"] = (to_mw(n, site, solar_geometry(n.index, site)) / site.ac_mw).clip(0, 1).to_numpy()
        p50 = f.predict(d)["p50"].to_numpy()
        r = {"n_hours": int(len(d)), "period": [str(d["time"].min()), str(d["time"].max())]}
        for truth in ("y", "y_nasa"):
            y = d[truth].to_numpy()
            r["era5" if truth == "y" else "nasa"] = {
                "model_p50": M.nmae(y, p50), "nwp_ensemble": M.nmae(y, d["phys_mean"]),
                **{"nwp_" + c.split("_")[1]: M.nmae(y, d[c].fillna(d["phys_mean"])) for c in NWP}}
        r["truths_agree_nmae"] = M.nmae(d["y"], d["y_nasa"])
        res[site.plant_id] = r
    return res


def elia(splits: tuple[str, ...]) -> dict:
    df = build_table(C.ELIA_SITES, "elia")
    fs = _forecasters(df)
    out = {}
    for site in C.ELIA_SITES:
        d = _rows(df, site.kind, splits)
        d = d[(d["plant_id"] == site.plant_id)].dropna(subset=["elia_p50"])
        tr = _rows(df, site.kind, ("train",))
        out[site.plant_id] = {"period": [str(d["time"].min()), str(d["time"].max())],
                              **_score(d, fs[site.kind], tr[tr["plant_id"] == site.plant_id], with_elia=True)}
    return out


# ---------------------------------------------------------------- sealed
def spatial() -> dict:
    from urja.data.fetch import fetch_all
    fetch_all(C.HELDOUT_SITES)
    dev = build_table()
    fs = _forecasters(dev)
    held = build_table(C.HELDOUT_SITES, "heldout_sites")
    out = {}
    for site in C.HELDOUT_SITES:
        d = _rows(held, site.kind, ("val", "test"))
        d = d[d["plant_id"] == site.plant_id]
        out[site.plant_id] = {"period": [str(d["time"].min()), str(d["time"].max())],
                              **_score(d, fs[site.kind], _rows(dev, site.kind, ("train",)), with_elia=False)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if a.final:
        out = C.RESULTS_DIR / "v3_sealed.json"
        if out.exists():
            sys.exit(f"{out} exists: the v3 sealed slices have been scored. See docs/V3_SEAL.md.")
        res = {"generated_utc": stamp, "lead_mode": C.LEAD_MODE, "spatial": spatial(), "elia_test": elia(("test",))}
    else:
        out = C.RESULTS_DIR / "v3_dev.json"
        res = {"generated_utc": stamp, "lead_mode": C.LEAD_MODE, "lead": lead_report(),
               "second_truth": second_truth(), "elia_dev": elia(("val",))}
    out.write_text(json.dumps(res, indent=2, default=float))
    print(json.dumps(res, indent=1, default=lambda x: round(float(x), 4))[:6000])
    print("wrote", out)


if __name__ == "__main__":
    main()
