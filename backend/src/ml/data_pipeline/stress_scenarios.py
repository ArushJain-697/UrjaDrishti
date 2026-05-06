"""
Day 4 — Stress Test Scenario Generator

Generates 4 separate stress test datasets for Person 4.
These are NOT training data — they are evaluation-only scenarios
injected into the trained model to test robustness.

Each scenario has the same 21 columns as feature_matrix_final.csv
so Person 4 can feed them directly into the inference pipeline.

Scenarios:
  1. Cloud ramp       — sudden CMF drop mid-afternoon on a clear day
  2. Monsoon onset    — 10-day progressive cloud buildup (early June)
  3. Wind speed spike — ramp from moderate to near cut-out and back
  4. Sustained low irradiance — week-long deep monsoon / haze event

All scenarios are generated for the relevant plant type.
Solar scenarios: PVG_S1 (representative solar plant)
Wind scenarios:  GAD_W1 (representative wind plant)
"""

import numpy as np
import pandas as pd
import os
import sys


from power_curve import power_curve_fraction
from nwp_ensemble import compute_solar_nwp_spread, compute_wind_nwp_spread

np.random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data")

# -----------------------------------------------------------------------
# SHARED HELPERS
# -----------------------------------------------------------------------

def make_timestamps(start_date, n_hours, tz="Asia/Kolkata"):
    return pd.date_range(start_date, periods=n_hours, freq="h", tz=tz)


def solar_diurnal_envelope(hour, doy, lat=14.5):
    """Same function as Day 1 — sun angle envelope."""
    decl = 23.45 * np.sin(np.deg2rad(360 / 365 * (doy - 81)))
    hour_angle = 15 * (hour - 12)
    cos_zenith = (
        np.sin(np.deg2rad(lat)) * np.sin(np.deg2rad(decl))
        + np.cos(np.deg2rad(lat)) * np.cos(np.deg2rad(decl))
        * np.cos(np.deg2rad(hour_angle))
    )
    return float(np.clip(cos_zenith, 0, 1))


def clearsky_ghi_approx(hour, doy, lat=14.5, linke=3.5):
    """
    Approximate clear-sky GHI using solar envelope × peak irradiance.
    For stress scenarios we use this approximation (not pvlib) to keep
    the scenario generator self-contained.
    """
    envelope = solar_diurnal_envelope(hour, doy, lat)
    # Peak clear-sky irradiance varies with Linke turbidity
    peak = 1000 * (1 - 0.05 * (linke - 2.0))
    return max(envelope * peak, 0.0)


def base_solar_row(ts, plant_id="PVG_S1", cluster_id="C1_Pavagada",
                   capacity_mw=150.0):
    """Template for a solar plant row with correct asset encodings."""
    lat, lon = 14.5, 77.2
    hour = ts.hour
    doy  = ts.dayofyear
    season = _season(ts.month)

    return {
        "timestamp":            ts,
        "plant_id":             plant_id,
        "plant_type":           "solar",
        "cluster_id":           cluster_id,
        "CMF":                  0.0,
        "power_curve_fraction": 0.0,
        "temperature":          28.0,
        "nwp_spread":           0.0,
        "capacity_mw":          capacity_mw,
        "lat_sin":              np.sin(np.deg2rad(lat)),
        "lat_cos":              np.cos(np.deg2rad(lat)),
        "lon_sin":              np.sin(np.deg2rad(lon)),
        "lon_cos":              np.cos(np.deg2rad(lon)),
        "tilt_angle_deg":       15.0,
        "hub_height_m":         0.0,
        "hour_sin":             np.sin(2 * np.pi * hour / 24),
        "hour_cos":             np.cos(2 * np.pi * hour / 24),
        "doy_sin":              np.sin(2 * np.pi * doy / 365),
        "doy_cos":              np.cos(2 * np.pi * doy / 365),
        "season":               season,
        "actual_generation_mw": 0.0,
    }


def base_wind_row(ts, plant_id="GAD_W1", cluster_id="C2_Gadag",
                  capacity_mw=100.0):
    """Template for a wind plant row with correct asset encodings."""
    lat, lon = 15.4, 75.6
    hour = ts.hour
    doy  = ts.dayofyear
    season = _season(ts.month)

    return {
        "timestamp":            ts,
        "plant_id":             plant_id,
        "plant_type":           "wind",
        "cluster_id":           cluster_id,
        "CMF":                  0.0,
        "power_curve_fraction": 0.0,
        "temperature":          26.0,
        "nwp_spread":           0.0,
        "capacity_mw":          capacity_mw,
        "lat_sin":              np.sin(np.deg2rad(lat)),
        "lat_cos":              np.cos(np.deg2rad(lat)),
        "lon_sin":              np.sin(np.deg2rad(lon)),
        "lon_cos":              np.cos(np.deg2rad(lon)),
        "tilt_angle_deg":       0.0,
        "hub_height_m":         100.0,
        "hour_sin":             np.sin(2 * np.pi * hour / 24),
        "hour_cos":             np.cos(2 * np.pi * hour / 24),
        "doy_sin":              np.sin(2 * np.pi * doy / 365),
        "doy_cos":              np.cos(2 * np.pi * doy / 365),
        "season":               season,
        "actual_generation_mw": 0.0,
    }


def _season(month):
    return {1:0,2:0,3:1,4:1,5:1,6:2,7:2,8:2,9:2,10:3,11:3,12:0}[month]


def finalize_solar_row(row, ghi, cloud_cover, cs_ghi, capacity_mw):
    """Fill CMF, generation, NWP spread for a solar row."""
    if cs_ghi < 5.0:
        row["CMF"]                  = 0.0
        row["actual_generation_mw"] = 0.0
        row["nwp_spread"]           = 0.0
        return row

    cmf = np.clip(ghi / cs_ghi, 0, 1)
    pr  = 0.75 * (1 - 0.003 * max(row["temperature"] - 25, 0))
    gen = np.clip(ghi / 1000 * pr * capacity_mw, 0, capacity_mw)

    # NWP spread
    spread = compute_solar_nwp_spread(
        pd.Series([ghi]),
        pd.Series([cloud_cover]),
        pd.Series([cs_ghi]),
    ).iloc[0]

    row["CMF"]                  = round(cmf, 4)
    row["actual_generation_mw"] = round(gen, 3)
    row["nwp_spread"]           = round(spread, 3)
    return row


def finalize_wind_row(row, wind_speed, capacity_mw, i=0, all_ws=None):
    """Fill power_curve_fraction, generation, NWP spread for a wind row."""
    pcf = power_curve_fraction(wind_speed)
    
    # Use generic power curve for generation (matches generate_data.py where actuals come from)
    gen_frac = 0.0
    if 3.0 <= wind_speed < 25.0:
        if wind_speed >= 12.0:
            gen_frac = 1.0
        else:
            gen_frac = ((wind_speed - 3.0) / (12.0 - 3.0)) ** 3
            
    # Add noise only when producing (matches generate_data.py)
    if gen_frac > 0:
        gen_frac = max(0.0, min(1.0, gen_frac + 0.0))  # Can't reliably import random here for noise, using mean
    
    gen = gen_frac * capacity_mw

    ws_series = pd.Series(all_ws) if all_ws is not None else pd.Series([wind_speed])
    spread = compute_wind_nwp_spread(ws_series).iloc[
        min(i, len(ws_series)-1)
    ]

    row["power_curve_fraction"] = round(float(pcf), 4)
    row["actual_generation_mw"] = round(float(gen), 3)
    row["nwp_spread"]           = round(float(spread), 3)
    return row


# -----------------------------------------------------------------------
# SCENARIO 1: SUDDEN CLOUD RAMP
# -----------------------------------------------------------------------

def generate_cloud_ramp(n_events=5):
    """
    Scenario 1: Sudden cloud ramp on a clear afternoon.

    Structure per event (48 hours):
      Hours 0-9:   Clear sky, CMF ~0.85-0.95
      Hours 10-11: CMF drops sharply from 0.85 → 0.15 (cloud front arrives)
      Hours 12-14: CMF stays at 0.15-0.20 (cloud cover)
      Hours 15-16: CMF recovers from 0.20 → 0.80 (cloud passes)
      Hours 17-23: Back to clear, CMF ~0.80-0.90
      Hours 24-47: Next day clear (recovery reference)

    5 events at different times of year to capture seasonal variation.
    """
    print("  Generating Scenario 1: Cloud Ramp...")

    # Different months for seasonal variety
    event_starts = [
        "2023-02-15 00:00",  # winter clear day
        "2023-04-20 00:00",  # summer pre-monsoon
        "2023-06-10 00:00",  # monsoon onset period
        "2023-09-05 00:00",  # late monsoon
        "2023-11-10 00:00",  # post-monsoon
    ]

    capacity_mw = 150.0
    all_rows = []

    for event_idx, start_str in enumerate(event_starts[:n_events]):
        timestamps = make_timestamps(start_str, 48)

        # Build wind speed profile for this event
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            doy  = ts.dayofyear
            cs_ghi = clearsky_ghi_approx(hour, doy)

            row = base_solar_row(ts, capacity_mw=capacity_mw)
            row["temperature"] = 30.0 + 3 * np.sin(np.pi * hour / 12)

            # Determine CMF based on hour within event
            if i < 10:
                # Pre-ramp: clear sky
                cmf = np.clip(0.90 + np.random.normal(0, 0.02), 0.80, 0.98)
                cloud = 0.05 + np.random.uniform(0, 0.05)

            elif i == 10:
                # Ramp begins — sharp CMF drop over 2 hours
                cmf   = 0.55
                cloud = 0.45

            elif i == 11:
                # Full cloud arrival
                cmf   = 0.15
                cloud = 0.85

            elif 12 <= i <= 14:
                # Deep cloud cover sustained
                cmf   = np.clip(0.15 + np.random.normal(0, 0.03), 0.05, 0.25)
                cloud = np.clip(0.85 + np.random.normal(0, 0.05), 0.75, 0.98)

            elif i == 15:
                # Recovery begins
                cmf   = 0.45
                cloud = 0.50

            elif i == 16:
                # Nearly clear again
                cmf   = 0.78
                cloud = 0.18

            elif 17 <= i <= 23:
                # Post-ramp clear
                cmf   = np.clip(0.85 + np.random.normal(0, 0.02), 0.78, 0.95)
                cloud = 0.05 + np.random.uniform(0, 0.05)

            else:
                # Day 2 — clear reference day
                cmf   = np.clip(0.88 + np.random.normal(0, 0.02), 0.80, 0.98)
                cloud = 0.03 + np.random.uniform(0, 0.04)

            ghi = cs_ghi * cmf
            row = finalize_solar_row(row, ghi, cloud, cs_ghi, capacity_mw)
            row["event_id"]   = f"cloud_ramp_{event_idx+1}"
            row["hour_in_event"] = i
            all_rows.append(row)

    df = pd.DataFrame(all_rows)
    print(f"    Generated {len(df)} rows, {len(event_starts)} events × 48 hours")
    print(f"    CMF range: {df['CMF'].min():.3f}–{df['CMF'].max():.3f}")
    print(f"    NWP spread range: {df['nwp_spread'].min():.2f}–"
          f"{df['nwp_spread'].max():.2f} W/m²")
    return df


# -----------------------------------------------------------------------
# SCENARIO 2: MONSOON ONSET
# -----------------------------------------------------------------------

def generate_monsoon_onset():
    """
    Scenario 2: Karnataka monsoon onset pattern.

    10 consecutive days (240 hours) starting early June.
    Progressive deterioration:
      Days 1-2:  Pre-monsoon, CMF ~0.65-0.75, cloud building
      Days 3-4:  First cloud bands, CMF drops to 0.35-0.50
      Days 5-6:  Monsoon arrives, CMF crashes to 0.10-0.25
      Days 7-8:  Peak monsoon, CMF 0.08-0.15
      Days 9-10: Established monsoon, CMF settles at 0.12-0.20

    NWP spread should widen dramatically as monsoon arrives —
    this is the hardest forecasting scenario.
    Temperature drops 5°C below seasonal norm as monsoon arrives.
    """
    print("  Generating Scenario 2: Monsoon Onset...")

    capacity_mw = 150.0
    start       = "2023-06-01 00:00"
    timestamps  = make_timestamps(start, 10 * 24)  # 10 days

    # CMF profile per day (mean daytime CMF)
    daily_cmf_mean = [0.72, 0.68, 0.50, 0.38, 0.22, 0.14, 0.10, 0.09, 0.12, 0.15]
    daily_cmf_std  = [0.05, 0.08, 0.12, 0.15, 0.10, 0.06, 0.04, 0.04, 0.05, 0.06]
    daily_cloud    = [0.28, 0.35, 0.55, 0.70, 0.85, 0.92, 0.95, 0.96, 0.93, 0.90]
    daily_temp_drop= [0.0,  0.5,  1.0,  2.0,  3.5,  5.0,  5.0,  5.0,  4.5,  4.0]

    all_rows = []
    for i, ts in enumerate(timestamps):
        day_idx = i // 24
        hour    = ts.hour
        doy     = ts.dayofyear

        cs_ghi  = clearsky_ghi_approx(hour, doy)
        row     = base_solar_row(ts, capacity_mw=capacity_mw)

        base_temp = 33.0
        row["temperature"] = base_temp - daily_temp_drop[day_idx] + \
                             np.random.normal(0, 0.5)

        if cs_ghi < 5.0:
            row["CMF"]                  = 0.0
            row["actual_generation_mw"] = 0.0
            row["nwp_spread"]           = 0.0
        else:
            cmf = np.clip(
                np.random.normal(daily_cmf_mean[day_idx],
                                 daily_cmf_std[day_idx]),
                0.02, 0.95
            )
            cloud = np.clip(
                daily_cloud[day_idx] + np.random.normal(0, 0.04),
                0.0, 1.0
            )
            ghi = cs_ghi * cmf
            row = finalize_solar_row(row, ghi, cloud, cs_ghi, capacity_mw)

        row["event_id"]      = "monsoon_onset"
        row["day_in_event"]  = day_idx + 1
        row["hour_in_event"] = i
        all_rows.append(row)

    df = pd.DataFrame(all_rows)

    # Summary by day
    day_summary = df[df["CMF"] > 0].groupby("day_in_event").agg(
        CMF_mean=("CMF", "mean"),
        spread_mean=("nwp_spread", "mean"),
        gen_mean=("actual_generation_mw", "mean"),
    ).round(3)

    print(f"    Generated {len(df)} rows (10 days × 24 hours)")
    print(f"    Day-by-day daytime CMF and spread:")
    print(day_summary.to_string())
    return df


# -----------------------------------------------------------------------
# SCENARIO 3: WIND SPEED SPIKE
# -----------------------------------------------------------------------

def generate_wind_spike(n_events=5):
    """
    Scenario 3: Wind speed spike approaching cut-out.

    Structure per event (72 hours):
      Hours 0-23:  Moderate wind baseline ~8 m/s, stable
      Hours 24-26: Wind ramps from 8 → 22 m/s over 3 hours
      Hours 27-29: Wind at 22-24 m/s (near cut-out, still generating)
      Hours 30-31: Wind crosses cut-out (>25 m/s), generation = 0
      Hours 32-34: Wind drops back below cut-out, generation resumes
      Hours 35-47: Recovery to moderate wind ~9 m/s
      Hours 48-71: Post-event stable reference

    This tests:
      - Power curve behaviour near cut-out
      - Whether uncertainty widens appropriately near threshold
      - Recovery detection
    """
    print("  Generating Scenario 3: Wind Speed Spike...")

    event_starts = [
        "2023-01-20 00:00",
        "2023-04-15 00:00",
        "2023-07-10 00:00",
        "2023-09-22 00:00",
        "2023-11-05 00:00",
    ]

    capacity_mw = 100.0
    all_rows    = []

    for event_idx, start_str in enumerate(event_starts[:n_events]):
        timestamps = make_timestamps(start_str, 72)
        all_ws     = []

        # Pre-compute wind speed profile
        for i in range(72):
            if i < 24:
                ws = 8.0 + np.random.normal(0, 0.5)
            elif i == 24:
                ws = 12.0
            elif i == 25:
                ws = 18.0
            elif i == 26:
                ws = 22.0
            elif 27 <= i <= 29:
                ws = np.clip(23.0 + np.random.normal(0, 0.5), 21.0, 24.5)
            elif i == 30:
                ws = 26.5   # above cut-out → shutdown
            elif i == 31:
                ws = 27.0   # still above cut-out
            elif i == 32:
                ws = 24.5   # back below cut-out → restart
            elif i == 33:
                ws = 20.0
            elif i == 34:
                ws = 15.0
            elif 35 <= i <= 47:
                ws = 9.0 + np.random.normal(0, 0.8)
            else:
                ws = 8.5 + np.random.normal(0, 0.5)

            all_ws.append(max(ws, 0.0))

        # Build rows
        for i, ts in enumerate(timestamps):
            row = base_wind_row(ts, capacity_mw=capacity_mw)
            ws  = all_ws[i]
            row = finalize_wind_row(row, ws, capacity_mw, i, all_ws)
            row["wind_speed_ms"]  = round(ws, 2)
            row["event_id"]       = f"wind_spike_{event_idx+1}"
            row["hour_in_event"]  = i
            all_rows.append(row)

    df = pd.DataFrame(all_rows)

    # Show the spike window
    spike_window = df[df["event_id"] == "wind_spike_1"][
        ["hour_in_event", "wind_speed_ms",
         "power_curve_fraction", "actual_generation_mw", "nwp_spread"]
    ].iloc[22:38]
    print(f"    Generated {len(df)} rows, {n_events} events × 72 hours")
    print(f"    Spike window (event 1, hours 22–37):")
    print(spike_window.to_string(index=False))
    return df


# -----------------------------------------------------------------------
# SCENARIO 4: SUSTAINED LOW IRRADIANCE
# -----------------------------------------------------------------------

def generate_sustained_low_irradiance():
    """
    Scenario 4: Week-long deep monsoon / haze event.

    7 consecutive days where CMF averages 0.10-0.20.
    Simulates deep monsoon conditions or a major haze episode.

    Structure:
      Days 1-7: CMF stays 0.08-0.22 all day, heavy cloud cover
      Temperature slightly suppressed (cloud blanket)
      NWP spread stays wide throughout — persistent uncertainty

    This tests whether the model degrades gracefully (wide intervals)
    rather than producing confident-but-wrong forecasts.
    """
    print("  Generating Scenario 4: Sustained Low Irradiance...")

    capacity_mw = 150.0
    start       = "2023-07-15 00:00"  # peak monsoon
    timestamps  = make_timestamps(start, 7 * 24)

    # Day-level CMF variation (slight daily fluctuation within low range)
    daily_cmf   = [0.12, 0.10, 0.18, 0.14, 0.09, 0.11, 0.15]
    daily_cloud = [0.92, 0.95, 0.88, 0.91, 0.96, 0.93, 0.90]

    all_rows = []
    for i, ts in enumerate(timestamps):
        day_idx = i // 24
        hour    = ts.hour
        doy     = ts.dayofyear

        cs_ghi = clearsky_ghi_approx(hour, doy)
        row    = base_solar_row(ts, capacity_mw=capacity_mw)

        # Temperature: monsoon suppresses temperature by 4-6°C
        row["temperature"] = 27.0 + np.random.normal(0, 0.8)

        if cs_ghi < 5.0:
            row["CMF"]                  = 0.0
            row["actual_generation_mw"] = 0.0
            row["nwp_spread"]           = 0.0
        else:
            cmf = np.clip(
                daily_cmf[day_idx] + np.random.normal(0, 0.03),
                0.04, 0.30
            )
            cloud = np.clip(
                daily_cloud[day_idx] + np.random.normal(0, 0.03),
                0.80, 1.0
            )
            ghi = cs_ghi * cmf
            row = finalize_solar_row(row, ghi, cloud, cs_ghi, capacity_mw)

        row["event_id"]      = "sustained_low_irradiance"
        row["day_in_event"]  = day_idx + 1
        row["hour_in_event"] = i
        all_rows.append(row)

    df = pd.DataFrame(all_rows)

    day_summary = df[df["CMF"] > 0].groupby("day_in_event").agg(
        CMF_mean=("CMF", "mean"),
        spread_mean=("nwp_spread", "mean"),
        gen_mean=("actual_generation_mw", "mean"),
    ).round(3)

    print(f"    Generated {len(df)} rows (7 days × 24 hours)")
    print(f"    Average daytime CMF: {df[df['CMF']>0]['CMF'].mean():.3f}")
    print(f"    Average NWP spread: {df[df['CMF']>0]['nwp_spread'].mean():.2f} W/m²")
    print(f"    Day-by-day summary:")
    print(day_summary.to_string())
    return df


# -----------------------------------------------------------------------
# MASTER GENERATOR
# -----------------------------------------------------------------------

def generate_all_stress_scenarios(save_dir=None):
    if save_dir is None:
        save_dir = DATA_DIR

    os.makedirs(save_dir, exist_ok=True)

    print("\nGenerating stress test scenarios...")
    print("(These are evaluation-only — NOT training data)\n")

    scenarios = {}

    # Scenario 1
    df1 = generate_cloud_ramp(n_events=5)
    path1 = os.path.join(save_dir, "stress_cloud_ramp.csv")
    df1.to_csv(path1, index=False)
    print(f"  Saved: stress_cloud_ramp.csv ({os.path.getsize(path1)//1024} KB)\n")
    scenarios["cloud_ramp"] = df1

    # Scenario 2
    df2 = generate_monsoon_onset()
    path2 = os.path.join(save_dir, "stress_monsoon_onset.csv")
    df2.to_csv(path2, index=False)
    print(f"  Saved: stress_monsoon_onset.csv ({os.path.getsize(path2)//1024} KB)\n")
    scenarios["monsoon_onset"] = df2

    # Scenario 3
    df3 = generate_wind_spike(n_events=5)
    path3 = os.path.join(save_dir, "stress_wind_spike.csv")
    df3.to_csv(path3, index=False)
    print(f"  Saved: stress_wind_spike.csv ({os.path.getsize(path3)//1024} KB)\n")
    scenarios["wind_spike"] = df3

    # Scenario 4
    df4 = generate_sustained_low_irradiance()
    path4 = os.path.join(save_dir, "stress_low_irradiance.csv")
    df4.to_csv(path4, index=False)
    print(f"  Saved: stress_low_irradiance.csv ({os.path.getsize(path4)//1024} KB)\n")
    scenarios["low_irradiance"] = df4

    return scenarios


if __name__ == "__main__":
    scenarios = generate_all_stress_scenarios()
    print("\nAll stress scenarios generated.")