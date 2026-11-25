"""L3: learned correction of NWP error, as a full predictive distribution.

* One global LightGBM per technology (solar, wind) per quantile level, trained on the
  `train` split only. Hyper-parameters are fixed (no tuning on calib or held-out data).
* Conformalized Quantile Regression (Romano et al., 2019) widens or narrows the P10-P90 band
  using the `calib` split, so the band's coverage is earned on data the model never trained on.
* Physical gate (deterministic, after the model): 0 <= q <= capacity, and solar is exactly 0
  when the sun is below the horizon. The model can never override it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import lightgbm as lgb
import numpy as np
import pandas as pd

from urja import config as C
from urja.uncertainty import tiers as T

LEVELS = tuple(round(x, 2) for x in np.arange(0.1, 0.91, 0.1))   # 0.1 ... 0.9
PARAMS = dict(learning_rate=0.05, num_leaves=31, min_child_samples=40, subsample=0.8, subsample_freq=1,
              colsample_bytree=0.8, reg_lambda=1.0, n_estimators=400, verbose=-1, random_state=C.SEED)


def gate(q: np.ndarray, daylight: np.ndarray | None) -> np.ndarray:
    """Deterministic physics gate. Sorts quantiles (no crossing), clips to [0, 1], zero at night."""
    q = np.sort(np.clip(q, 0.0, 1.0), axis=1)
    if daylight is not None:
        q[~np.asarray(daylight, bool)] = 0.0
    return q


@dataclass
class QuantileForecaster:
    kind: str
    cols: list[str]
    models: dict = field(default_factory=dict)
    mondrian: bool = True        # per-tier conformal (True) or one global correction (ablation)
    qhat: dict = field(default_factory=dict)   # CQR correction per tier, capacity units

    def _rows(self, df: pd.DataFrame) -> pd.DataFrame:
        d = df[df["kind"] == self.kind]
        return d[d["daylight"]] if self.kind == "solar" else d

    def fit(self, df: pd.DataFrame) -> "QuantileForecaster":
        tr = self._rows(df[df["split"] == "train"])
        for a in LEVELS:
            m = lgb.LGBMRegressor(objective="quantile", alpha=a, **PARAMS)
            m.fit(tr[self.cols], tr["y"])
            self.models[a] = m
        return self

    def raw(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.cols]
        q = np.column_stack([self.models[a].predict(X) for a in LEVELS])
        return gate(q, df["daylight"].to_numpy() if self.kind == "solar" else None)

    def tiers(self, df: pd.DataFrame, q: np.ndarray) -> np.ndarray:
        return T.assign(q[:, -1] - q[:, 0], df["phys_range"].to_numpy())

    @staticmethod
    def _conformal(scores: np.ndarray, alpha: float) -> float:
        n = len(scores)
        return float(np.quantile(scores, min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)))

    def calibrate(self, df: pd.DataFrame, alpha: float = 0.2) -> "QuantileForecaster":
        cal = self._rows(df[df["split"] == "calib"])
        q = self.raw(cal)
        y = cal["y"].to_numpy()
        scores = np.maximum(q[:, 0] - y, y - q[:, -1])
        glob = self._conformal(scores, alpha)
        if not self.mondrian:
            self.qhat = {t: glob for t in T.TIERS}
            return self
        tier = self.tiers(cal, q)
        for t in T.TIERS:
            s = scores[tier == t]
            # A tier with too few calibration points falls back to the global correction.
            self.qhat[t] = self._conformal(s, alpha) if len(s) >= 50 else glob
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Returns q10..q90 (raw), p10/p50/p90 (P10/P90 conformalised and gated)."""
        q = self.raw(df)
        out = pd.DataFrame(q, columns=[f"q{int(a * 100)}" for a in LEVELS], index=df.index)
        day = df["daylight"].to_numpy() if self.kind == "solar" else np.ones(len(df), bool)
        tier = self.tiers(df, q)
        qh = np.array([self.qhat[t] for t in tier])
        band = np.column_stack([q[:, 0] - qh, q[:, 4], q[:, -1] + qh])
        band = gate(band, day)
        out["p10"], out["p50"], out["p90"] = band[:, 0], band[:, 1], band[:, 2]
        out["tier"] = tier
        return out
