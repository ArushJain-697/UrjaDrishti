"""Shared by both model families. Deliberately imports neither LightGBM nor PyTorch: on macOS the
two ship different OpenMP runtimes and deadlock in one process (see docs/BUILD_LOG.md)."""
from __future__ import annotations

import numpy as np

LEVELS = tuple(round(x, 2) for x in np.arange(0.1, 0.91, 0.1))   # 0.1 ... 0.9


def gate(q: np.ndarray, daylight: np.ndarray | None) -> np.ndarray:
    """Deterministic physics gate. Sorts quantiles (no crossing), clips to [0, 1], zero at night."""
    q = np.sort(np.clip(q, 0.0, 1.0), axis=1)
    if daylight is not None:
        q[~np.asarray(daylight, bool)] = 0.0
    return q
