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
from urja.models.common import LEVELS, gate
from urja.uncertainty import tiers as T

PARAMS = dict(learning_rate=0.05, num_leaves=31, min_child_samples=40, subsample=0.8, subsample_freq=1,
              colsample_bytree=0.8, reg_lambda=1.0, n_estimators=400, verbose=-1, random_state=C.SEED)


@dataclass
class QuantileForecaster:
    kind: str
    cols: list[str]
    models: dict = field(default_factory=dict)
    mondrian: bool = True        # per-tier conformal (True) or one global correction (ablation)
    blend: bool = True           # shift the distribution toward the NWP-ensemble mean (weight fit on data)
    w_ens: float = 0.0           # 0 = LightGBM median, 1 = NWP-ensemble mean
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

    def _lgbm(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.cols]
        return np.column_stack([self.models[a].predict(X) for a in LEVELS])

    def raw(self, df: pd.DataFrame) -> np.ndarray:
        q = self._lgbm(df)
        if self.w_ens:
            # Forecast combination: move the whole distribution so its median sits at
            # (1 - w) * LightGBM median + w * NWP-ensemble mean. Width is unchanged.
            ens = df["phys_mean"].fillna(pd.Series(q[:, 4], index=df.index)).to_numpy()
            q = q + (self.w_ens * (ens - q[:, 4]))[:, None]
        return gate(q, df["daylight"].to_numpy() if self.kind == "solar" else None)

    def _calib_rows(self, df: pd.DataFrame, half: int) -> pd.DataFrame:
        """Calibration weeks split in two: half 0 fits the blend weight, half 1 the conformal step."""
        cal = self._rows(df[df["split"] == "calib"])
        week = pd.to_datetime(cal["time"]).dt.isocalendar().week.astype(int)
        return cal[(week // C.CALIB_EVERY_NTH_WEEK) % 2 == half]

    def fit_blend(self, df: pd.DataFrame) -> "QuantileForecaster":
        if not self.blend:
            self.w_ens = 0.0
            return self
        cal = self._calib_rows(df, 0)
        q50, ens, y = self._lgbm(cal)[:, 4], cal["phys_mean"].to_numpy(), cal["y"].to_numpy()
        ok = ~np.isnan(ens)
        grid = np.round(np.arange(0, 1.0001, 0.05), 2)
        err = [np.mean(np.abs(np.clip((1 - w) * q50[ok] + w * ens[ok], 0, 1) - y[ok])) for w in grid]
        self.w_ens = float(grid[int(np.argmin(err))])
        return self

    def tiers(self, df: pd.DataFrame, q: np.ndarray) -> np.ndarray:
        return T.assign(q[:, -1] - q[:, 0], df["phys_range"].to_numpy())

    @staticmethod
    def _conformal(scores: np.ndarray, alpha: float) -> float:
        n = len(scores)
        return float(np.quantile(scores, min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)))

    def calibrate(self, df: pd.DataFrame, alpha: float = 0.2) -> "QuantileForecaster":
        self.fit_blend(df)
        # If the data chose w = 0 the model is the plain LightGBM, so all calibration weeks are used.
        cal = self._calib_rows(df, 1) if self.w_ens else self._rows(df[df["split"] == "calib"])
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
