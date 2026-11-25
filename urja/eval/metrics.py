"""Scores. All errors are normalised by plant AC capacity (y is already generation / capacity).
Solar is scored on daylight hours only: counting night hours (always 0, always right) would
roughly halve every solar error and make every method look better than it is."""
from __future__ import annotations

import numpy as np

from urja import config as C


def nmae(y, p) -> float:
    return float(np.mean(np.abs(np.asarray(p) - np.asarray(y))))


def nrmse(y, p) -> float:
    return float(np.sqrt(np.mean((np.asarray(p) - np.asarray(y)) ** 2)))


def pinball(y, q, levels) -> float:
    y = np.asarray(y)[:, None]
    q = np.asarray(q)
    lv = np.asarray(levels)[None, :]
    d = y - q
    return float(np.mean(np.maximum(lv * d, (lv - 1) * d)))


def crps_from_quantiles(y, q, levels) -> float:
    """CRPS ~= 2 x mean pinball loss over evenly spaced quantile levels."""
    return 2.0 * pinball(y, q, levels)


def crps_ensemble(y, members) -> float:
    """Exact CRPS of an equally weighted ensemble (fair baseline for the 3 raw NWP models)."""
    y = np.asarray(y)[:, None]
    m = np.asarray(members)
    t1 = np.mean(np.abs(m - y), axis=1)
    t2 = 0.5 * np.mean(np.abs(m[:, :, None] - m[:, None, :]), axis=(1, 2))
    return float(np.mean(t1 - t2))


def coverage(y, lo, hi) -> float:
    y = np.asarray(y)
    return float(np.mean((y >= lo) & (y <= hi)))


def width(lo, hi) -> float:
    return float(np.mean(np.asarray(hi) - np.asarray(lo)))


def dsm_excess(y, schedule) -> float:
    """Energy outside the +-free band, as a fraction of capacity-hours (CERC-DSM-shaped proxy)."""
    dev = np.abs(np.asarray(y) - np.asarray(schedule))
    return float(np.mean(np.maximum(dev - C.DSM_FREE_BAND, 0.0)))
