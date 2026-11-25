"""Evaluation harness. Every number in the README comes from the JSON this writes.

    python -m urja.eval.run            # validation split (Apr-Oct 2025): used for design choices
    python -m urja.eval.run --final    # sealed test year (Nov 2025-Oct 2026): run ONCE

Baselines are the ones an operator could actually use, not strawmen:
  persistence    actual generation at the same hour yesterday (generous: a real day-ahead
                 schedule is filed before yesterday's afternoon is known)
  climatology    mean of the train split for (plant, month, hour)
  nwp_<model>    the physics model run on ONE weather model's day-ahead forecast
  nwp_ensemble   the physics model on all three, averaged (the strongest no-ML baseline)
  linear_mos     ridge regression on the three physics forecasts (classic post-processing)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from urja import config as C
from urja.eval import metrics as M
from urja.features.build import build_table, feature_columns
from urja.models.quantile import LEVELS, QuantileForecaster
from urja.uncertainty.tiers import TIERS

NWP_PHYS = ["phys_ecmwf", "phys_gfs", "phys_icon"]
ABLATIONS = {
    # name: column prefixes removed from the model's inputs
    "no_disagreement": ("phys_std", "phys_range", "ws_std", "cloud_std"),
    "single_nwp_icon": ("phys_ecmwf", "ghi_ecmwf", "ws_ecmwf", "cloud_ecmwf", "temp_ecmwf",
                        "phys_gfs", "ghi_gfs", "ws_gfs", "cloud_gfs", "temp_gfs",
                        "phys_mean", "phys_std", "phys_range", "ws_std", "cloud_std"),
    "no_physics_prior": ("phys_", "ceiling"),
}


def _scored(df: pd.DataFrame, kind: str, split: str) -> pd.DataFrame:
    d = df[(df["kind"] == kind) & (df["split"] == split)]
    return d[d["daylight"]] if kind == "solar" else d


def _point(y, p) -> dict:
    return {"nmae": M.nmae(y, p), "nrmse": M.nrmse(y, p), "dsm_excess": M.dsm_excess(y, p)}


def _filled(d: pd.DataFrame) -> pd.DataFrame:
    """The three physics forecasts, a rare missing model hour replaced by the other models' mean."""
    return d[NWP_PHYS].apply(lambda c: c.fillna(d["phys_mean"]))


def baselines(df: pd.DataFrame, kind: str, split: str) -> dict:
    full = df[df["kind"] == kind].sort_values(["plant_id", "time"]).copy()
    full["persistence"] = full.groupby("plant_id")["y"].shift(24)
    tr = full[full["split"] == "train"]
    clim = tr.groupby([tr["plant_id"], tr["time"].dt.month, tr["time"].dt.hour])["y"].mean()
    full["climatology"] = [clim.get((p, t.month, t.hour), np.nan) for p, t in zip(full["plant_id"], full["time"])]
    X = _filled(tr)
    mos = Ridge(alpha=1.0).fit(X if kind == "wind" else X[tr["daylight"]], tr["y"] if kind == "wind" else tr.loc[tr["daylight"], "y"])
    Xa = _filled(full)
    full["linear_mos"] = np.clip(mos.predict(Xa), 0, 1)

    d = full[full["split"] == split]
    d = d[d["daylight"]] if kind == "solar" else d
    d = d.dropna(subset=["persistence"])
    y = d["y"].to_numpy()
    out = {}
    for name in ["persistence", "climatology", "linear_mos"]:
        out[name] = _point(y, d[name].to_numpy())
    for c in NWP_PHYS:
        out["nwp_" + c.split("_")[1]] = _point(y, d[c].fillna(d["phys_mean"]).to_numpy())
    out["nwp_ensemble"] = _point(y, d["phys_mean"].to_numpy())
    members = _filled(d).to_numpy()
    out["nwp_ensemble"]["crps"] = M.crps_ensemble(y, members)
    out["nwp_ensemble"]["coverage_minmax"] = M.coverage(y, members.min(1), members.max(1))
    # Climatological quantiles of the train split as a probabilistic floor.
    tq = tr.groupby([tr["plant_id"], tr["time"].dt.month, tr["time"].dt.hour])["y"].quantile(list(LEVELS)).unstack()
    keys = list(zip(d["plant_id"], d["time"].dt.month, d["time"].dt.hour))
    qs = tq.reindex(keys).to_numpy()
    out["climatology"]["crps"] = M.crps_from_quantiles(y, qs, LEVELS)
    out["climatology"]["coverage_80"] = M.coverage(y, qs[:, 0], qs[:, -1])
    return out


def score_model(f: QuantileForecaster, d: pd.DataFrame) -> dict:
    p = f.predict(d)
    y = d["y"].to_numpy()
    q = p[[c for c in p.columns if c.startswith("q")]].to_numpy()
    res = _point(y, p["p50"].to_numpy())
    res.update(crps=M.crps_from_quantiles(y, q, LEVELS),
               coverage_80=M.coverage(y, p["p10"], p["p90"]),
               width_80=M.width(p["p10"], p["p90"]),
               qhat={k: round(v, 4) for k, v in f.qhat.items()})
    tiers = {}
    dev = np.abs(y - p["p50"].to_numpy())
    excess = np.maximum(dev - C.DSM_FREE_BAND, 0)
    for t in TIERS:
        m = (p["tier"] == t).to_numpy()
        if m.sum() == 0:
            continue
        tiers[t] = {"share_hours": float(m.mean()), "nmae": float(dev[m].mean()),
                    "coverage_80": M.coverage(y[m], p["p10"][m], p["p90"][m]),
                    "share_dsm_excess": float(excess[m].sum() / max(excess.sum(), 1e-12))}
    res["tiers"] = tiers
    return res


def run(split: str) -> dict:
    df = build_table()
    cols = feature_columns(df)
    result = {"split": split, "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "period": {"val": [C.VAL_START, C.TEST_START], "test": [C.TEST_START, C.PERIOD_END]}[split],
              "n_features": len(cols), "kinds": {}}
    for kind in ("solar", "wind"):
        d = _scored(df, kind, split)
        k = {"n_hours": int(len(d)), "baselines": baselines(df, kind, split)}
        main = QuantileForecaster(kind, cols).fit(df).calibrate(df)
        k["model"] = score_model(main, d)
        glob = QuantileForecaster(kind, cols, mondrian=False, models=main.models, mos=main.mos).calibrate(df)
        k["ablation"] = {"global_conformal": score_model(glob, d)}
        for name, drop in ABLATIONS.items():
            c2 = feature_columns(df, drop)
            k["ablation"][name] = score_model(QuantileForecaster(kind, c2).fit(df).calibrate(df), d)
        best = min((v["nmae"], n) for n, v in k["baselines"].items())
        k["best_baseline"] = best[1]
        b = k["baselines"]["nwp_ensemble"]
        k["vs_nwp_ensemble"] = {
            "nmae_reduction": 1 - k["model"]["nmae"] / b["nmae"],
            "crps_reduction": 1 - k["model"]["crps"] / b["crps"],
            "dsm_excess_reduction": 1 - k["model"]["dsm_excess"] / b["dsm_excess"],
        }
        bb = k["baselines"][k["best_baseline"]]
        k["vs_best_baseline"] = {
            "name": k["best_baseline"],
            "nmae_reduction": 1 - k["model"]["nmae"] / bb["nmae"],
            "dsm_excess_reduction": 1 - k["model"]["dsm_excess"] / bb["dsm_excess"],
        }
        result["kinds"][kind] = k
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true", help="score the sealed test year (once)")
    a = ap.parse_args()
    split = "test" if a.final else "val"
    out = C.RESULTS_DIR / f"metrics_{split}.json"
    if a.final and out.exists():
        sys.exit(f"{out} already exists: the test year has been scored. Delete it only with a BUILD_LOG entry saying why.")
    res = run(split)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, default=float))
    for kind, k in res["kinds"].items():
        m, b = k["model"], k["baselines"]["nwp_ensemble"]
        print(f"[{split}] {kind}: nMAE {m['nmae']:.4f} vs NWP-ens {b['nmae']:.4f} | CRPS {m['crps']:.4f} vs {b['crps']:.4f}"
              f" | cov80 {m['coverage_80']:.3f} | DSM {m['dsm_excess']:.4f} vs {b['dsm_excess']:.4f} | best baseline {k['best_baseline']}")
    print("wrote", out)


if __name__ == "__main__":
    main()
