"""L5: the day-ahead schedule. Deterministic: no model decides what gets filed with the SLDC.

Rule:
  schedule_mw = P50 x capacity            (the median minimises expected absolute deviation)
  RED hour    -> review_required = True   (a dispatcher must look before the schedule is filed)
  The schedule can never exceed capacity or be negative, and solar is 0 at night (physics gate
  already applied to P50).
Nothing about this rule is learned; tests/test_decision.py pins it.
"""
from __future__ import annotations

import pandas as pd

from urja.uncertainty.tiers import RED


def schedule(pred: pd.DataFrame, capacity_mw: float) -> pd.DataFrame:
    out = pd.DataFrame(index=pred.index)
    out["schedule_mw"] = (pred["p50"].clip(0, 1) * capacity_mw).round(2)
    out["p10_mw"] = (pred["p10"] * capacity_mw).round(2)
    out["p90_mw"] = (pred["p90"] * capacity_mw).round(2)
    out["tier"] = pred["tier"]
    out["review_required"] = pred["tier"] == RED
    return out
