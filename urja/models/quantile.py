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
from sklearn.linear_model import Ridge

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
    blend: bool = True           # shift the distribution toward a no-ML anchor (anchor + weight fit on data)
    w_ens: float = 0.0           # 0 = LightGBM median, 1 = the anchor
    anchor: str = "ens"          # "ens" = raw NWP-ensemble mean, "mos" = ridge on the 3 physics forecasts
    mos: object = None
    qhat: dict = field(default_factory=dict)   # CQR correction per tier, capacity units

    def _rows(self, df: pd.DataFrame) -> pd.DataFrame:
        d = df[df["kind"] == self.kind]
        return d[d["daylight"]] if self.kind == "solar" else d

    @staticmethod
    def _nwp(d: pd.DataFrame) -> pd.DataFrame:
        cols = ["phys_ecmwf", "phys_gfs", "phys_icon"]
        return d[cols].apply(lambda c: c.fillna(d["phys_mean"])).fillna(0)

    def anchor_values(self, d: pd.DataFrame, anchor: str | None = None) -> np.ndarray:
        if (anchor or self.anchor) == "mos":
            return np.clip(self.mos.predict(self._nwp(d)), 0, 1)
        return d["phys_mean"].to_numpy()

    def fit(self, df: pd.DataFrame) -> "QuantileForecaster":
        tr = self._rows(df[df["split"] == "train"])
        self.mos = Ridge(alpha=1.0).fit(self._nwp(tr), tr["y"])
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
            anc = self.anchor_values(df)
            anc = np.where(np.isnan(anc), q[:, 4], anc)
            q = q + (self.w_ens * (anc - q[:, 4]))[:, None]
        return gate(q, df["daylight"].to_numpy() if self.kind == "solar" else None)

    def fit_blend(self, df: pd.DataFrame, folds: int = 4) -> "QuantileForecaster":
        """Choose the anchor (ens / mos) and weight from OUT-OF-FOLD predictions on the train split.

        Folds are blocked by calendar month (month mod `folds`), so each fold's LightGBM median and
        ridge MOS never saw the months they predict. This uses a whole year of data for a 2-parameter
        choice; choosing on ~6 calibration weeks picked the wrong anchor for both Belgian series (BUILD_LOG).
        """
        if not self.blend:
            self.anchor, self.w_ens = "ens", 0.0
            return self
        tr = self._rows(df[df["split"] == "train"]).copy()
        fold = pd.to_datetime(tr["time"]).dt.month.to_numpy() % folds
        q50, mos = np.full(len(tr), np.nan), np.full(len(tr), np.nan)
        for k in range(folds):
            fit, hold = tr[fold != k], fold == k
            m = lgb.LGBMRegressor(objective="quantile", alpha=0.5, **PARAMS).fit(fit[self.cols], fit["y"])
            q50[hold] = m.predict(tr.loc[hold, self.cols])
            mos[hold] = np.clip(Ridge(alpha=1.0).fit(self._nwp(fit), fit["y"]).predict(self._nwp(tr[hold])), 0, 1)
        y, ens = tr["y"].to_numpy(), tr["phys_mean"].to_numpy()
        grid = np.round(np.arange(0.05, 1.0001, 0.05), 2)
        best = (np.mean(np.abs(np.clip(q50, 0, 1) - y)), "ens", 0.0)
        for anchor, a in (("ens", ens), ("mos", mos)):
            ok = ~np.isnan(a)
            for w in grid:
                e = np.mean(np.abs(np.clip((1 - w) * q50[ok] + w * a[ok], 0, 1) - y[ok]))
                if e < best[0]:
                    best = (e, anchor, float(w))
        _, self.anchor, self.w_ens = best
        return self

    def tiers(self, df: pd.DataFrame, q: np.ndarray) -> np.ndarray:
        return T.assign(q[:, -1] - q[:, 0], df["phys_range"].to_numpy())

    @staticmethod
    def _conformal(scores: np.ndarray, alpha: float) -> float:
        n = len(scores)
        return float(np.quantile(scores, min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)))

    def calibrate(self, df: pd.DataFrame, alpha: float = 0.2) -> "QuantileForecaster":
        self.fit_blend(df)                       # uses the train split only (out-of-fold)
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
