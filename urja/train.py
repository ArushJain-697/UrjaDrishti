"""Fit the forecasters on the train split, calibrate on calib, and write replay predictions.

    python -m urja.train

Writes artifacts/forecaster_<kind>.joblib and artifacts/replay.parquet (every hour of every
split, with P10/P50/P90, tier and the deterministic schedule). The API only exposes test-year
days after results/metrics_test.json exists, so the dashboard cannot leak the sealed year.
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd

from urja import config as C
from urja.decision.schedule import schedule
from urja.features.build import build_table, feature_columns
from urja.models.quantile import QuantileForecaster
from urja.uncertainty.tiers import GREEN


def main() -> None:
    df = build_table()
    cols = feature_columns(df)
    C.ART_DIR.mkdir(parents=True, exist_ok=True)
    parts = []
    for kind in ("solar", "wind"):
        f = QuantileForecaster(kind, cols).fit(df).calibrate(df)
        joblib.dump(f, C.ART_DIR / f"forecaster_{kind}.joblib")
        d = df[df["kind"] == kind]
        p = f.predict(d)
        if kind == "solar":                        # night hours: physics says 0, tier GREEN
            night = ~d["daylight"].to_numpy()
            p.loc[night, ["p10", "p50", "p90"]] = 0.0
            p.loc[night, "tier"] = GREEN
        for pid, g in d.groupby("plant_id"):
            s = schedule(p.loc[g.index], C.SITE_BY_ID[pid].ac_mw)
            part = pd.concat([g[["time", "plant_id", "kind", "split", "actual_mw"]],
                              (g[["phys_ecmwf", "phys_gfs", "phys_icon"]] * C.SITE_BY_ID[pid].ac_mw).round(2),
                              s], axis=1)
            parts.append(part)
    rep = pd.concat(parts).sort_values(["plant_id", "time"])
    rep["actual_mw"] = rep["actual_mw"].round(2)
    rep.to_parquet(C.ART_DIR / "replay.parquet")
    print("rows", len(rep), "| RED share", np.round(rep["review_required"].mean(), 3))


if __name__ == "__main__":
    main()
