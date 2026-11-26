"""L3b: a small quantile MLP, the edge-deployable twin of the LightGBM model.

Why it exists: trees are fast on any CPU, but a neural net can be exported to ONNX/ExecuTorch,
quantised to int8 and run on SIMD / dot-product kernels on a substation-side device.
Same features, same 9 quantile levels, same conformal + physics gate afterwards.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from torch import nn

from urja import config as C
from urja.models.common import LEVELS


# Standard deviations are floored at 1e-2: a constant feature (e.g. the wind "ceiling") has std ~0,
# and 1e-6 underflows to 0 in fp16, turning the normalisation into a divide-by-zero (BUILD_LOG #17).
class QuantileMLP(nn.Module):
    def __init__(self, n_in: int, hidden: int = 64, n_q: int = len(LEVELS)):
        super().__init__()
        self.mu = nn.Parameter(torch.zeros(n_in), requires_grad=False)
        self.sd = nn.Parameter(torch.ones(n_in), requires_grad=False)
        self.net = nn.Sequential(nn.Linear(n_in, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU(),
                                 nn.Linear(hidden, n_q))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = (x - self.mu) / self.sd
        base = self.net(x)
        # Monotone quantiles by construction: first level + cumulative softplus increments.
        return torch.cat([base[:, :1], base[:, :1] + torch.cumsum(nn.functional.softplus(base[:, 1:]), 1)], 1)


def _xy(d: pd.DataFrame, cols: list[str]) -> tuple[np.ndarray, np.ndarray]:
    X = d[cols].to_numpy(np.float32)
    X = np.where(np.isnan(X), 0.0, X).astype(np.float32)    # rare missing ICON hour
    return X, d["y"].to_numpy(np.float32)


def train(df: pd.DataFrame, kind: str, cols: list[str], epochs: int = 60) -> QuantileMLP:
    torch.manual_seed(C.SEED)
    tr = df[(df["kind"] == kind) & (df["split"] == "train")]
    tr = tr[tr["daylight"]] if kind == "solar" else tr
    X, y = _xy(tr, cols)
    m = QuantileMLP(X.shape[1])
    m.mu.data = torch.tensor(X.mean(0))
    m.sd.data = torch.tensor(np.maximum(X.std(0), 1e-2))
    lv = torch.tensor(LEVELS, dtype=torch.float32)[None, :]
    opt = torch.optim.AdamW(m.parameters(), lr=2e-3, weight_decay=1e-4)
    Xt, yt = torch.tensor(X), torch.tensor(y)[:, None]
    for _ in range(epochs):
        perm = torch.randperm(len(Xt))
        for i in range(0, len(Xt), 256):
            b = perm[i:i + 256]
            d = yt[b] - m(Xt[b])
            loss = torch.maximum(lv * d, (lv - 1) * d).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
    return m.eval()


def predict(m: QuantileMLP, d: pd.DataFrame, cols: list[str]) -> np.ndarray:
    X, _ = _xy(d, cols)
    with torch.no_grad():
        return m(torch.tensor(X)).numpy()
