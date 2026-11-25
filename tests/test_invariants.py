"""Named invariants. Each test name states the claim it protects."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from urja import config as C
from urja.decision.schedule import schedule
from urja.features.build import assign_split
from urja.models.common import gate
from urja.physics.power import wind_power_mw
from urja.uncertainty import tiers as T

ROOT = Path(__file__).resolve().parent.parent
HAVE_DATA = (C.RAW_DIR / f"truth_{C.SITES[0].plant_id}.parquet").exists()


# ---- Leakage: features must not move when the truth moves ---------------------------------
@pytest.mark.skipif(not HAVE_DATA, reason="run python -m urja.data.fetch first")
def test_no_truth_leaks_into_features(monkeypatch):
    from urja.features import build as B
    site = C.SITES[2]
    clean = B._site_table(site)
    real = B.fetch_truth

    def scrambled(s):
        t = real(s).copy()
        rng = np.random.default_rng(0)
        for c in t.columns:
            t[c] = rng.permutation(t[c].to_numpy())
        return t

    monkeypatch.setattr(B, "fetch_truth", scrambled)
    dirty = B._site_table(site)
    feats = [c for c in clean.columns if c not in B.META + ["kind"]]
    pd.testing.assert_frame_equal(clean[feats], dirty[feats])
    assert not np.allclose(clean["y"], dirty["y"]), "the target should change when truth changes"


# ---- Splits are time-ordered and disjoint --------------------------------------------------
def test_splits_are_time_ordered_and_sealed():
    t = pd.Series(pd.date_range(C.PERIOD_START, C.PERIOD_END + " 23:00", freq="h", tz=C.TZ))
    s = assign_split(t)
    assert t[s == "test"].min() == pd.Timestamp(C.TEST_START, tz=C.TZ)
    assert t[s == "val"].max() < t[s == "test"].min()
    assert t[s.isin(["train", "calib"])].max() < t[s == "val"].min()
    assert set(s.unique()) == {"train", "calib", "val", "test"}


# ---- Physics gate --------------------------------------------------------------------------
@settings(max_examples=300)
@given(st.lists(st.lists(st.floats(-2, 3, allow_nan=False), min_size=9, max_size=9), min_size=1, max_size=40),
       st.data())
def test_gate_never_emits_impossible_power(rows, data):
    q = np.array(rows)
    day = np.array(data.draw(st.lists(st.booleans(), min_size=len(rows), max_size=len(rows))))
    g = gate(q, day)
    assert (g >= 0).all() and (g <= 1).all()
    assert (np.diff(g, axis=1) >= 0).all(), "quantiles must not cross"
    assert (g[~day] == 0).all(), "no solar power at night"


@settings(max_examples=300)
@given(st.floats(0, 40, allow_nan=False), st.floats(0, 40, allow_nan=False))
def test_wind_curve_is_monotone_until_cut_out(a, b):
    site = C.SITES[2]
    lo, hi = sorted((a, b))
    if hi < C.WIND_CUT_OUT:
        assert wind_power_mw(np.array([lo]), site)[0] <= wind_power_mw(np.array([hi]), site)[0] + 1e-9
    assert wind_power_mw(np.array([C.WIND_CUT_OUT + 0.1]), site)[0] == 0.0
    assert wind_power_mw(np.array([C.WIND_CUT_IN - 0.1]), site)[0] == 0.0


# ---- Tiers: more uncertainty can never make an hour look safer ------------------------------
TIER_RANK = {T.GREEN: 0, T.AMBER: 1, T.RED: 2}


@settings(max_examples=500)
@given(st.floats(0, 1), st.floats(0, 1), st.floats(0, 0.5), st.floats(0, 0.5))
def test_tier_is_monotone_in_uncertainty(w, r, dw, dr):
    a = T.assign(np.array([w]), np.array([r]))[0]
    b = T.assign(np.array([w + dw]), np.array([r + dr]))[0]
    assert TIER_RANK[b] >= TIER_RANK[a]


# ---- Conformal: the band earns its coverage on exchangeable data ---------------------------
def test_conformal_correction_reaches_target_coverage():
    from urja.models.quantile import QuantileForecaster
    rng = np.random.default_rng(1)
    n = 4000
    y = rng.normal(0.5, 0.2, n)
    # Deliberately too-narrow raw band: +-0.1 around the mean (true 80% half-width ~0.256)
    raw = np.column_stack([np.full(n, 0.4)] + [np.full(n, 0.5)] * 7 + [np.full(n, 0.6)])
    scores = np.maximum(raw[:, 0] - y, y - raw[:, -1])
    qh = QuantileForecaster._conformal(scores[:2000], 0.2)
    test = y[2000:]
    cov = np.mean((test >= 0.4 - qh) & (test <= 0.6 + qh))
    assert 0.77 <= cov <= 0.83


# ---- The schedule is a fixed rule, never above capacity ------------------------------------
def test_schedule_is_deterministic_and_bounded():
    p = pd.DataFrame({"p10": [0.0, 0.2, 0.5], "p50": [0.1, 0.6, 1.3], "p90": [0.2, 0.9, 1.0],
                      "tier": [T.GREEN, T.AMBER, T.RED]})
    s = schedule(p, 100.0)
    assert s["schedule_mw"].tolist() == [10.0, 60.0, 100.0]
    assert s["review_required"].tolist() == [False, False, True]
    pd.testing.assert_frame_equal(s, schedule(p, 100.0))


# ---- Config-literal guard: site coordinates live only in config.py -------------------------
def test_site_constants_only_in_config():
    pats = [re.compile(rf"\b{s.lat:.2f}\b.*\b{s.lon:.2f}\b") for s in C.SITES]
    for f in (ROOT / "urja").rglob("*.py"):
        if f.name == "config.py":
            continue
        txt = f.read_text()
        assert not any(p.search(txt) for p in pats), f"site coordinates hard-coded in {f}"


# ---- The dashboard cannot show the sealed test year before it is scored --------------------
@pytest.mark.skipif(not (C.ART_DIR / "replay.parquet").exists(), reason="run python -m urja.train first")
def test_api_hides_test_year_until_scored(monkeypatch):
    from fastapi.testclient import TestClient

    from urja.api import app as A
    monkeypatch.setattr(A, "_test_unsealed", lambda: False)
    c = TestClient(A.app)
    days = c.get("/api/days").json()
    assert all(d["split"] == "val" for d in days)
    assert c.get("/api/day/2026-01-10").status_code == 404


# ---- v3: no forecast run published after the filing deadline is ever used ------------------
@settings(max_examples=200)
@given(st.integers(0, 900), st.sampled_from([s.plant_id for s in C.SITES + C.ELIA_SITES]))
def test_filed_lead_never_uses_a_run_published_after_the_deadline(day_offset, sid):
    from urja.data.lead import filing_deadline_utc, run_day_needed
    site = C.SITE_BY_ID[sid]
    idx = pd.date_range(pd.Timestamp(C.PERIOD_START, tz="UTC") + pd.Timedelta(days=day_offset), periods=24, freq="h").tz_convert(site.tz)
    n = run_day_needed(idx, site)
    assert set(np.unique(n)) <= {1, 2}
    init = (idx.tz_convert("UTC") - pd.to_timedelta(n, unit="D")).floor(f"{C.RUN_EVERY_H}h")
    published = init + pd.Timedelta(hours=C.PUBLISH_LATENCY_H)
    assert (published <= filing_deadline_utc(idx, site)).all()


def test_karnataka_hours_after_0530_need_the_day2_run():
    from urja.data.lead import run_day_needed
    site = C.SITE_BY_ID["PVG_S1"]
    idx = pd.date_range("2025-06-10 00:30", periods=24, freq="h", tz=site.tz)   # true IST hour-ends
    n = dict(zip(idx.hour, run_day_needed(idx, site)))
    assert all(n[h] == 1 for h in range(0, 5)) and all(n[h] == 2 for h in range(6, 24))


@pytest.mark.skipif(not HAVE_DATA, reason="run python -m urja.data.fetch first")
def test_karnataka_rows_sit_on_true_utc_hours():
    """Regression for BUILD_LOG #13: rows must be whole UTC hours (IST :30), not IST whole hours."""
    from urja.data.fetch import fetch_truth
    t = fetch_truth(C.SITES[0]).index
    assert (t.tz_convert("UTC").minute == 0).all()
    assert (t.minute == 30).all()
