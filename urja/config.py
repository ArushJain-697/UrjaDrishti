"""Every constant in one place. Tests fail if a site constant appears as a literal elsewhere.

Sites are real Karnataka renewable locations; the capacities are *modelled* 100 MW AC blocks,
not the real plants' nameplate (the real SCADA data is not public). See docs/HONESTY.md.
"""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
ART_DIR = ROOT / "artifacts"
RESULTS_DIR = ROOT / "results"
TZ = "Asia/Kolkata"


@dataclass(frozen=True)
class Site:
    plant_id: str
    name: str
    kind: str          # "solar" | "wind"
    lat: float
    lon: float
    ac_mw: float = 100.0


SITES = (
    Site("PVG_S1", "Pavagada Solar Park", "solar", 14.10, 77.28),
    Site("KPL_S1", "Koppal solar block", "solar", 15.35, 76.15),
    Site("GDG_W1", "Gadag (Kappatagudda) wind", "wind", 15.33, 75.63),
    Site("CTD_W1", "Chitradurga (Jogimatti) wind", "wind", 14.17, 76.40),
)
SITE_BY_ID = {s.plant_id: s for s in SITES}

# Three independent global NWP models. Their disagreement is a signal, not noise.
NWP_MODELS = ("ecmwf_ifs025", "gfs_global", "icon_global")
NWP_VARS = ("shortwave_radiation", "temperature_2m", "wind_speed_100m", "cloud_cover")
TRUTH_VARS = ("shortwave_radiation", "temperature_2m", "wind_speed_100m", "cloud_cover")

# Day-ahead lead: the value each model forecast for hour t, from the run ~24 h earlier.
LEAD_SUFFIX = "_previous_day1"

# ECMWF IFS 0.25 deg previous-run archive starts in spring 2024.
PERIOD_START = "2024-04-01"
PERIOD_END = "2025-10-31"

# Split. The held-out window is touched once, by eval/heldout.py, after all choices are frozen.
TRAIN_END = "2025-03-31"          # train + calibration live before this date
HELDOUT_START = "2025-04-01"      # pre-monsoon, monsoon and post-monsoon 2025
CALIB_EVERY_NTH_WEEK = 4          # every 4th ISO week of the dev period is the conformal calibration set

# Physics
PV_DC_AC_RATIO = 1.25             # 125 MWp DC behind 100 MW AC -> midday clipping
PV_TILT_DEG = 14.0                # ~latitude, south facing
PV_GAMMA = -0.0037                # per degC, crystalline Si
WIND_CUT_IN, WIND_RATED, WIND_CUT_OUT = 3.0, 12.0, 25.0   # m/s, generic IEC class II curve

# Uncertainty tiers (from normalised P10-P90 width). Fixed on the dev set, frozen before held-out.
TIER_AMBER_WIDTH = 0.20           # band wider than 20% of capacity -> AMBER
TIER_RED_WIDTH = 0.40             # wider than 40% of capacity -> RED: dispatcher must review
TIER_RED_DISAGREEMENT = 0.25      # NWP models disagree by >25% of capacity -> RED regardless

# Deviation settlement (simplified CERC DSM shape: free band, then penalty per MWh).
DSM_FREE_BAND = 0.10              # +-10% of AC capacity, no charge
DSM_PENALTY_PER_MWH = 1.0         # unit cost; we report relative savings, never rupees

QUANTILES = (0.1, 0.5, 0.9)
SEED = 42
