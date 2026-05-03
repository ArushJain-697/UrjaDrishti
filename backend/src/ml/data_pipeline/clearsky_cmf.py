"""
Day 2 — Part 1: Ineichen-Perez Clear Sky Model + Cloud Modification Factor

For every solar plant, every hour:
  1. Compute clear-sky GHI using pvlib Ineichen-Perez
  2. Derive CMF = actual_GHI / clearsky_GHI  (clipped 0-1)
  3. Mark nighttime hours (clearsky_GHI < 5 W/m²) as CMF = NaN

CMF is the primary solar feature going to Person 2.
Raw GHI is NOT passed forward.

Why CMF instead of raw GHI:
  - Raw GHI varies enormously by time of day and season
  - CMF = 1.0 means perfectly clear sky regardless of season/location
  - CMF = 0.0 means complete cloud cover
  - A model trained on CMF generalises across all seasons and geographies
"""

import pvlib
import pandas as pd
import numpy as np

# Linke turbidity for Karnataka by month
# Source: SoDa database typical values for Deccan plateau
# Higher in monsoon (aerosols + humidity), lower in winter
LINKE_TURBIDITY_MONTHLY = {
    1: 3.0,   # January  — winter, clear
    2: 3.2,   # February
    3: 3.5,   # March
    4: 3.8,   # April    — pre-monsoon haze building
    5: 4.2,   # May      — peak haze
    6: 4.5,   # June     — monsoon onset
    7: 4.5,   # July     — peak monsoon
    8: 4.3,   # August
    9: 4.0,   # September
    10: 3.5,  # October  — post-monsoon clearing
    11: 3.2,  # November
    12: 3.0,  # December — winter, clear
}

# Solar plant locations from asset registry
SOLAR_PLANTS = {
    "PVG_S1": {"lat": 14.50, "lon": 77.20, "alt": 700},
    "PVG_S2": {"lat": 14.52, "lon": 77.25, "alt": 710},
    "MIX_S1": {"lat": 14.48, "lon": 77.18, "alt": 690},
}

# Threshold below which we treat it as nighttime
NIGHT_THRESHOLD_WM2 = 5.0


def get_linke_turbidity_series(timestamps):
    """
    Returns a Series of Linke turbidity values matching the timestamp index.
    One value per hour based on month.
    """
    months = pd.to_datetime(timestamps).month
    return months.map(LINKE_TURBIDITY_MONTHLY)


def compute_clearsky_ghi(plant_id, timestamps):
    """
    Compute clear-sky GHI for a solar plant using Ineichen-Perez model.

    Parameters
    ----------
    plant_id : str
    timestamps : DatetimeIndex (timezone-aware, Asia/Kolkata)

    Returns
    -------
    Series : clear-sky GHI in W/m² for each timestamp
    """
    coords = SOLAR_PLANTS[plant_id]

    location = pvlib.location.Location(
        latitude=coords["lat"],
        longitude=coords["lon"],
        tz="Asia/Kolkata",
        altitude=coords["alt"],
        name=plant_id,
    )

    # Monthly Linke turbidity — pvlib accepts a Series aligned to the timestamps
    linke = get_linke_turbidity_series(timestamps)
    linke.index = timestamps

    clearsky = location.get_clearsky(
        times=timestamps,
        model="ineichen",
        linke_turbidity=linke,
    )

    return clearsky["ghi"]  # W/m²


def derive_cmf(actual_ghi, clearsky_ghi):
    """
    Compute Cloud Modification Factor.

    CMF = actual_GHI / clearsky_GHI
    - Clipped to [0, 1]
    - NaN at nighttime (clearsky_GHI < NIGHT_THRESHOLD_WM2)
    - NaN when actual_GHI is NaN

    Parameters
    ----------
    actual_ghi   : Series — measured/synthetic GHI (W/m²)
    clearsky_ghi : Series — Ineichen-Perez clear-sky GHI (W/m²)

    Returns
    -------
    Series : CMF values
    """
    cmf = actual_ghi / clearsky_ghi

    # Clip to physical range
    cmf = cmf.clip(lower=0.0, upper=1.0)

    # Nighttime: clearsky GHI below threshold → CMF is meaningless
    nighttime_mask = clearsky_ghi < NIGHT_THRESHOLD_WM2
    cmf[nighttime_mask] = np.nan

    # Also NaN if actual GHI itself is NaN
    cmf[actual_ghi.isna()] = np.nan

    return cmf


def process_all_solar_plants(df_raw):
    """
    Takes the raw weather DataFrame from Day 1.
    For each solar plant, computes clearsky_GHI and CMF.
    Returns a DataFrame with new columns added.

    Parameters
    ----------
    df_raw : DataFrame — output of Day 1 (raw_weather_data.csv)

    Returns
    -------
    DataFrame with added columns: clearsky_GHI, CMF
    """
    df = df_raw.copy()
    df["clearsky_GHI"] = np.nan
    df["CMF"] = np.nan

    solar_plants = df[df["plant_type"] == "solar"]["plant_id"].unique()

    for plant_id in solar_plants:
        print(f"  Computing clear-sky GHI for {plant_id}...")

        mask = df["plant_id"] == plant_id
        plant_df = df[mask].copy()

        # Ensure timestamps are timezone-aware
        timestamps = pd.to_datetime(plant_df["timestamp"])
        if timestamps.dt.tz is None:
            timestamps = timestamps.dt.tz_localize("Asia/Kolkata")
        else:
            timestamps = timestamps.dt.tz_convert("Asia/Kolkata")

        timestamps = pd.DatetimeIndex(timestamps)

        # Compute clear-sky GHI
        cs_ghi = compute_clearsky_ghi(plant_id, timestamps)
        cs_ghi.index = plant_df.index

        # Compute CMF
        actual_ghi = plant_df["GHI"].values
        cmf = derive_cmf(
            pd.Series(actual_ghi, index=plant_df.index),
            cs_ghi,
        )

        df.loc[mask, "clearsky_GHI"] = cs_ghi.values
        df.loc[mask, "CMF"] = cmf.values

        # Summary
        day_mask = mask & (df["clearsky_GHI"] >= NIGHT_THRESHOLD_WM2)
        day_cmf = df.loc[day_mask, "CMF"]
        print(f"    Clear-sky GHI range: {cs_ghi.min():.1f}–{cs_ghi.max():.1f} W/m²")
        print(f"    CMF (daytime): mean={day_cmf.mean():.3f}, "
              f"min={day_cmf.min():.3f}, max={day_cmf.max():.3f}")

    return df


if __name__ == "__main__":
    # Quick standalone test
    import pandas as pd
    times = pd.date_range("2023-01-01", periods=8760, freq="h", tz="Asia/Kolkata")
    cs = compute_clearsky_ghi("PVG_S1", times)
    print("Clear-sky GHI sample (June noon):")
    june_noon = cs[cs.index.month == 6][cs.index.hour == 12]
    print(june_noon.head(5))
    print(f"\nAnnual max: {cs.max():.1f} W/m²")
    print(f"Night hours (GHI=0): {(cs < 5).sum()}")