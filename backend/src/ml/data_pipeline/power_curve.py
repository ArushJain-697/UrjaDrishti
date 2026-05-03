"""
Day 2 — Part 2: Turbine Power Curve Transform

Converts raw wind speed (at hub height) into a generation fraction [0, 1].

Why this matters:
  - Wind speed to power is a cubic + clipped relationship — non-linear
  - Cut-in (~3 m/s) and cut-out (~25 m/s) thresholds create hard zeros
  - Letting an ML model learn this from scratch is wasteful and fragile
  - The physics transform handles it explicitly; the model learns residuals only

Turbine used: Suzlon S111 2.1 MW — common in Karnataka (Gadag region)
Power curve values from manufacturer datasheet (publicly available).
Using numpy.interp for accurate interpolation between tabulated points.
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# SUZLON S111 2.1 MW Power Curve
# Source: Suzlon Energy datasheet / thewindpower.net
# Wind speed in m/s → power output as fraction of rated capacity
# ---------------------------------------------------------------------------

# Tabulated (wind_speed_ms, power_fraction) pairs
# power_fraction = actual_power / rated_capacity
SUZLON_S111_CURVE = [
    (0.0,  0.000),
    (1.0,  0.000),
    (2.0,  0.000),
    (3.0,  0.000),   # cut-in speed
    (4.0,  0.020),
    (5.0,  0.057),
    (6.0,  0.113),
    (7.0,  0.192),
    (8.0,  0.301),
    (9.0,  0.430),
    (10.0, 0.573),
    (11.0, 0.719),
    (12.0, 0.856),
    (13.0, 0.944),
    (14.0, 0.981),
    (15.0, 0.995),
    (16.0, 1.000),   # rated speed — full output from here
    (17.0, 1.000),
    (18.0, 1.000),
    (19.0, 1.000),
    (20.0, 1.000),
    (21.0, 1.000),
    (22.0, 1.000),
    (23.0, 1.000),
    (24.0, 1.000),
    (25.0, 1.000),   # cut-out speed — shutdown above this
    (25.1, 0.000),   # hard shutdown
    (35.0, 0.000),
]

# Separate into arrays for numpy.interp
_WS_POINTS  = np.array([p[0] for p in SUZLON_S111_CURVE])
_PWR_POINTS = np.array([p[1] for p in SUZLON_S111_CURVE])

CUT_IN  = 3.0
CUT_OUT = 25.0


def power_curve_fraction(wind_speed_ms):
    """
    Convert wind speed (m/s) to generation fraction [0, 1] using
    Suzlon S111 tabulated power curve with linear interpolation.

    Parameters
    ----------
    wind_speed_ms : float or array-like — wind speed at hub height (m/s)

    Returns
    -------
    float or ndarray — generation fraction [0, 1]
    """
    ws = np.asarray(wind_speed_ms, dtype=float)

    # numpy.interp handles the interpolation between tabulated points
    fraction = np.interp(ws, _WS_POINTS, _PWR_POINTS)

    # Enforce hard cut-in and cut-out (belt-and-suspenders)
    fraction = np.where(ws < CUT_IN,  0.0, fraction)
    fraction = np.where(ws > CUT_OUT, 0.0, fraction)
    fraction = np.clip(fraction, 0.0, 1.0)

    # Return scalar if input was scalar
    return float(fraction) if np.ndim(wind_speed_ms) == 0 else fraction


def power_curve_mw(wind_speed_ms, capacity_mw):
    """
    Convert wind speed to absolute generation in MW.

    Parameters
    ----------
    wind_speed_ms : float or array-like
    capacity_mw   : float — installed capacity

    Returns
    -------
    float or ndarray — generation in MW
    """
    return power_curve_fraction(wind_speed_ms) * capacity_mw


def process_all_wind_plants(df_raw):
    """
    Takes the raw weather DataFrame from Day 1.
    For each wind plant, computes power_curve_fraction from wind_speed.
    Returns DataFrame with new column added: power_curve_fraction

    The power curve is applied to wind_speed which was already
    hub-height-corrected in Day 1's generate_wind_plant().

    Parameters
    ----------
    df_raw : DataFrame — output of Day 1

    Returns
    -------
    DataFrame with added column: power_curve_fraction
    """
    df = df_raw.copy()
    df["power_curve_fraction"] = np.nan

    wind_plants = df[df["plant_type"] == "wind"]["plant_id"].unique()

    for plant_id in wind_plants:
        print(f"  Applying power curve transform for {plant_id}...")

        mask = df["plant_id"] == plant_id
        ws = df.loc[mask, "wind_speed"].values

        pcf = power_curve_fraction(ws)
        df.loc[mask, "power_curve_fraction"] = pcf

        # Summary
        operating = pcf[(ws >= CUT_IN) & (ws <= CUT_OUT)]
        print(f"    Wind speed range: {ws.min():.2f}–{ws.max():.2f} m/s")
        print(f"    Power curve fraction — mean (operating): {operating.mean():.3f}, "
              f"max: {pcf.max():.3f}")
        print(f"    Hours at full output (PCF=1.0): {(pcf == 1.0).sum()}")
        print(f"    Hours cut-out shutdown: {((ws > CUT_OUT)).sum()}")

    return df


def print_curve_table():
    """Print the power curve for documentation / verification."""
    print(f"{'Wind Speed (m/s)':>18} {'Power Fraction':>16} {'Notes':>20}")
    print("-" * 58)
    for ws, pf in SUZLON_S111_CURVE:
        note = ""
        if ws == CUT_IN:  note = "<-- cut-in"
        if ws == 16.0:    note = "<-- rated speed"
        if ws == CUT_OUT: note = "<-- cut-out"
        if ws == 25.1:    note = "<-- hard shutdown"
        print(f"{ws:>18.1f} {pf:>16.3f} {note:>20}")


if __name__ == "__main__":
    print_curve_table()
    print("\nSpot checks:")
    for ws in [0, 2.9, 3.0, 5.0, 10.0, 16.0, 20.0, 25.0, 25.5, 30.0]:
        print(f"  ws={ws:5.1f} m/s → PCF={power_curve_fraction(ws):.4f}")