"""
Day 3 — Part 1: NWP Ensemble Spread Simulation

In real operations, weather forecasting models (NWP = Numerical Weather
Prediction) are run as ensembles — typically 10-50 slightly perturbed
runs of the same model. The spread (standard deviation) across those
runs directly encodes atmospheric uncertainty.

High spread = atmosphere is in an unstable state = forecast is uncertain
Low spread  = stable atmosphere = forecast is confident

We simulate this by:
  1. Taking the base weather variable (GHI for solar, wind speed for wind)
  2. Generating N=10 perturbed versions with Gaussian noise
  3. The noise scale is proportional to atmospheric instability:
       - Solar: scales with cloud cover (cloudy = more uncertain)
       - Wind:  scales with wind speed variance (gusty = more uncertain)
  4. Computing std across the 10 members = ensemble spread feature

This spread is then passed as an input feature to LightGBM (Person 2)
and also feeds directly into the CQR uncertainty layer — wide spread
automatically widens the prediction interval.

Key behavior to verify:
  - Clear sunny days: spread near zero
  - Monsoon / heavy cloud: spread large
  - Wind calm periods: spread small
  - Wind ramp events: spread large
"""

import numpy as np
import pandas as pd

N_ENSEMBLE_MEMBERS = 10
np.random.seed(42)


def compute_solar_nwp_spread(ghi_series, cloud_cover_series, clearsky_ghi_series):
    """
    Simulate NWP ensemble spread for solar irradiance.

    Uncertainty scale depends on:
      - Cloud cover fraction (higher cloud = more uncertain)
      - Absolute GHI level (more energy = more to be uncertain about)
      - Whether we're in a transition state (CMF changing rapidly)

    Parameters
    ----------
    ghi_series        : Series — actual GHI (W/m²)
    cloud_cover_series: Series — cloud cover fraction [0,1]
    clearsky_ghi_series: Series — clear-sky GHI from Ineichen-Perez

    Returns
    -------
    Series — NWP ensemble spread for solar (W/m²)
    """
    ghi        = ghi_series.values
    cloud      = cloud_cover_series.values
    cs_ghi     = clearsky_ghi_series.values

    n_hours = len(ghi)
    spreads = np.zeros(n_hours)

    for i in range(n_hours):
        g  = ghi[i]
        cl = cloud[i]
        cs = cs_ghi[i]

        # Nighttime — no solar uncertainty
        if cs < 5.0 or g < 0.5:
            spreads[i] = 0.0
            continue

        # Base uncertainty: 5% of clear-sky GHI minimum
        base_uncertainty = 0.05 * cs

        # Cloud contribution: up to 30% additional uncertainty
        # Heavy cloud = very uncertain where patches will be
        cloud_contribution = 0.30 * cl * cs

        # Total uncertainty scale for this hour
        sigma = base_uncertainty + cloud_contribution

        # Generate N perturbed ensemble members
        members = g + np.random.normal(0, sigma, N_ENSEMBLE_MEMBERS)
        members = np.clip(members, 0, cs * 1.1)  # can't exceed ~clear sky

        spreads[i] = members.std()

    return pd.Series(spreads, index=ghi_series.index, name="nwp_spread_solar")


def compute_wind_nwp_spread(wind_speed_series, recent_variance_window=6):
    """
    Simulate NWP ensemble spread for wind speed.

    Uncertainty scale depends on:
      - Recent wind speed variance (gusty conditions = more uncertain)
      - Absolute wind speed level (higher speed = larger absolute uncertainty)
      - Proximity to cut-in/cut-out thresholds (most critical for generation)

    Parameters
    ----------
    wind_speed_series      : Series — wind speed at hub height (m/s)
    recent_variance_window : int — hours of recent history to compute variance

    Returns
    -------
    Series — NWP ensemble spread for wind (m/s)
    """
    ws = wind_speed_series.values
    n  = len(ws)
    spreads = np.zeros(n)

    for i in range(n):
        w = ws[i]

        # Recent variance: how gusty has it been in last 6 hours
        start = max(0, i - recent_variance_window)
        recent_ws = ws[start:i+1]
        recent_var = recent_ws.std() if len(recent_ws) > 1 else 0.5

        # Base uncertainty: 12% of current wind speed
        base_sigma = max(0.12 * w, 0.3)   # minimum 0.3 m/s

        # Gustiness adds uncertainty
        gust_sigma = 0.5 * recent_var

        # Near cut-in (2-5 m/s): extra uncertainty — small errors have
        # large generation impact because of cubic curve slope
        cutin_proximity = max(0, 1 - abs(w - 3.0) / 3.0)
        cutin_sigma = 0.8 * cutin_proximity

        # Near cut-out (22-28 m/s): extra uncertainty — shutdown risk
        cutout_proximity = max(0, 1 - abs(w - 25.0) / 5.0)
        cutout_sigma = 1.5 * cutout_proximity

        total_sigma = base_sigma + gust_sigma + cutin_sigma + cutout_sigma

        # Generate ensemble members
        members = w + np.random.normal(0, total_sigma, N_ENSEMBLE_MEMBERS)
        members = np.clip(members, 0, 40)

        spreads[i] = members.std()

    return pd.Series(spreads, index=wind_speed_series.index, name="nwp_spread_wind")


def add_nwp_spread_to_dataframe(df, raw_physics_df):
    """
    Adds nwp_spread column to the feature matrix for all plants.

    For solar plants: spread based on GHI + cloud cover
    For wind plants:  spread based on wind speed variance

    Parameters
    ----------
    df              : DataFrame — feature matrix (from Day 2)
    raw_physics_df  : DataFrame — raw_with_physics.csv (has clearsky_GHI)

    Returns
    -------
    DataFrame — feature matrix with nwp_spread column added
    """
    df = df.copy()
    df["nwp_spread"] = 0.0

    solar_plants = df[df["plant_type"] == "solar"]["plant_id"].unique()
    wind_plants  = df[df["plant_type"] == "wind"]["plant_id"].unique()

    # --- Solar plants ---
    for plant_id in solar_plants:
        print(f"  Computing NWP spread for {plant_id} (solar)...")

        mask    = df["plant_id"] == plant_id
        raw_mask = raw_physics_df["plant_id"] == plant_id

        plant_df    = df[mask].copy()
        raw_plant   = raw_physics_df[raw_mask].copy()

        # Align index
        plant_df    = plant_df.reset_index(drop=True)
        raw_plant   = raw_plant.reset_index(drop=True)

        spread = compute_solar_nwp_spread(
            ghi_series         = pd.Series(raw_plant["GHI"].values),
            cloud_cover_series = pd.Series(raw_plant["cloud_cover"].values),
            clearsky_ghi_series= pd.Series(raw_plant["clearsky_GHI"].values),
        )

        df.loc[mask, "nwp_spread"] = spread.values

        # Summary
        day_spread = spread[raw_plant["clearsky_GHI"].values >= 5]
        print(f"    Daytime spread: mean={day_spread.mean():.2f}, "
              f"max={day_spread.max():.2f} W/m²")

    # --- Wind plants ---
    for plant_id in wind_plants:
        print(f"  Computing NWP spread for {plant_id} (wind)...")

        mask     = df["plant_id"] == plant_id
        raw_mask = raw_physics_df["plant_id"] == plant_id

        raw_plant = raw_physics_df[raw_mask].reset_index(drop=True)

        spread = compute_wind_nwp_spread(
            wind_speed_series = pd.Series(raw_plant["wind_speed"].values),
        )

        df.loc[mask, "nwp_spread"] = spread.values

        print(f"    Wind spread: mean={spread.mean():.3f}, "
              f"max={spread.max():.3f} m/s")

    return df


if __name__ == "__main__":
    # Spot checks
    print("Solar spread spot checks:")
    import pandas as pd
    ghi   = pd.Series([0, 0, 200, 600, 900, 300, 50, 0])
    cloud = pd.Series([0, 0, 0.8, 0.3, 0.1, 0.7, 0.9, 0])
    cs    = pd.Series([0, 0, 400, 700, 950, 600, 200, 0])
    spread = compute_solar_nwp_spread(ghi, cloud, cs)
    for i, (g, cl, s) in enumerate(zip(ghi, cloud, spread)):
        print(f"  GHI={g:4.0f}, cloud={cl:.1f} → spread={s:.2f} W/m²")

    print("\nWind spread spot checks:")
    ws = pd.Series([0, 2, 3, 8, 12, 20, 25, 26, 30])
    spread_w = compute_wind_nwp_spread(ws)
    for w, s in zip(ws, spread_w):
        print(f"  ws={w:5.1f} m/s → spread={s:.3f} m/s")