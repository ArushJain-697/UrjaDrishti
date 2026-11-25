"""L4: confidence tiers, decided BEFORE conformal calibration and from forecast-time signals only.

GREEN  narrow raw band and the three NWP models roughly agree -> schedule automatically
AMBER  band of moderate width                                  -> schedule, dispatcher notified
RED    wide band, or the NWP models disagree strongly          -> dispatcher must review the schedule

The tier is also the Mondrian group for conformal calibration: each tier earns its own
P10-P90 coverage instead of borrowing it from easy hours (the Flat-Band Trap).
"""
from __future__ import annotations

import numpy as np

from urja import config as C

GREEN, AMBER, RED = "GREEN", "AMBER", "RED"
TIERS = (GREEN, AMBER, RED)


def assign(raw_width: np.ndarray, nwp_range: np.ndarray) -> np.ndarray:
    w = np.asarray(raw_width, float)
    r = np.asarray(nwp_range, float)
    tier = np.full(w.shape, GREEN, dtype=object)
    tier[w >= C.TIER_AMBER_WIDTH] = AMBER
    tier[(w >= C.TIER_RED_WIDTH) | (r >= C.TIER_RED_DISAGREEMENT)] = RED
    return tier
