"""
Fetch seed data from NASA POWER API for Pavagada and Gadag.
This is public data — no SCADA, no restrictions.
Used only to get the correlation structure for the Gaussian Copula.
API docs: https://power.larc.nasa.gov/docs/services/api/
"""

import requests
import pandas as pd
import numpy as np
import os

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"

# Parameters we need:
# ALLSKY_SFC_SW_DWN = GHI (W/m²)
# T2M              = Temperature at 2m (°C)
# CLOUD_AMT        = Cloud amount (%)
# WS10M            = Wind speed at 10m (m/s)
# WD10M            = Wind direction at 10m (degrees)

SOLAR_PARAMS = "ALLSKY_SFC_SW_DWN,T2M,CLOUD_AMT"
WIND_PARAMS  = "WS10M,WD10M,T2M"

LOCATIONS = {
    "pavagada": {"lat": 14.5,  "lon": 77.2, "params": SOLAR_PARAMS},
    "gadag":    {"lat": 15.4,  "lon": 75.6, "params": WIND_PARAMS},
}

# Pull one year as seed (2022)
START = "20220101"
END   = "20221231"


def fetch_nasa_power(lat, lon, params, start=START, end=END):
    """
    Calls NASA POWER hourly API and returns a clean DataFrame.
    Returns None if the API is unreachable (fallback to synthetic seed).
    """
    payload = {
        "parameters": params,
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": start,
        "end": end,
        "format": "JSON",
        "time-standard": "UTC",
    }

    try:
        resp = requests.get(NASA_POWER_URL, params=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        hourly = data["properties"]["parameter"]
        df = pd.DataFrame(hourly)

        # NASA POWER timestamps are YYYYMMDDHH strings — convert to datetime
        df.index = pd.to_datetime(df.index, format="%Y%m%d%H", utc=True)
        df.index.name = "timestamp"

        # Replace NASA fill value (-999) with NaN
        df = df.replace(-999.0, np.nan)
        df = df.replace(-999, np.nan)

        return df

    except Exception as e:
        print(f"  WARNING: NASA POWER fetch failed ({e}). Will use synthetic seed.")
        return None


def build_solar_seed(df_nasa):
    """
    From NASA POWER solar data, build a seed DataFrame for copula fitting.
    Columns: GHI, temperature, cloud_cover_fraction, generation_fraction
    generation_fraction is derived: simple linear model from GHI for seeding purposes.
    """
    seed = pd.DataFrame(index=df_nasa.index)
    seed["GHI"]               = df_nasa["ALLSKY_SFC_SW_DWN"].clip(lower=0)
    seed["temperature"]       = df_nasa["T2M"]
    seed["cloud_cover"]       = (df_nasa["CLOUD_AMT"] / 100).clip(0, 1)  # 0-1 fraction

    # Approximate generation: GHI drives output, temperature slightly reduces it
    # PR (performance ratio) ~ 0.75 for Karnataka climate
    # gen_fraction = GHI / 1000 * PR, clipped 0-1
    seed["generation_fraction"] = (seed["GHI"] / 1000 * 0.75 * (1 - 0.003 * (seed["temperature"] - 25))).clip(0, 1)

    # Drop nighttime rows (GHI < 5 W/m²) — copula should only see daylight hours
    seed = seed[seed["GHI"] >= 5].dropna()
    return seed


def build_wind_seed(df_nasa):
    """
    From NASA POWER wind data, build a seed DataFrame for copula fitting.
    Columns: wind_speed, wind_direction, generation_fraction
    """
    seed = pd.DataFrame(index=df_nasa.index)

    # Scale 10m wind to hub height (100m) using power law: v_h = v_10 * (h/10)^alpha
    # alpha = 0.143 (Hellmann exponent for open terrain)
    alpha = 0.143
    hub_height = 100
    seed["wind_speed"]     = df_nasa["WS10M"] * (hub_height / 10) ** alpha
    seed["wind_direction"] = df_nasa["WD10M"]
    seed["temperature"]    = df_nasa["T2M"]

    # Approximate generation fraction using simple power curve logic
    seed["generation_fraction"] = seed["wind_speed"].apply(_simple_power_curve)

    seed = seed.dropna()
    return seed


def _simple_power_curve(ws, cut_in=3, rated=12, cut_out=25):
    if ws < cut_in or ws > cut_out:
        return 0.0
    elif ws >= rated:
        return 1.0
    else:
        return ((ws - cut_in) / (rated - cut_in)) ** 3


def make_synthetic_solar_seed(n=2000):
    """
    Fallback: generate a physically plausible solar seed without NASA data.
    Used when NASA API is unreachable.
    """
    np.random.seed(42)
    GHI         = np.random.uniform(50, 900, n)
    temperature = 25 + 0.01 * GHI + np.random.normal(0, 3, n)
    cloud_cover = np.clip(1 - GHI / 1000 + np.random.normal(0, 0.1, n), 0, 1)
    gen_frac    = np.clip(GHI / 1000 * 0.75 * (1 - 0.003 * (temperature - 25)), 0, 1)

    return pd.DataFrame({
        "GHI": GHI,
        "temperature": temperature,
        "cloud_cover": cloud_cover,
        "generation_fraction": gen_frac,
    })


def make_synthetic_wind_seed(n=2000):
    """
    Fallback: generate a physically plausible wind seed without NASA data.
    """
    np.random.seed(43)
    wind_speed     = np.random.weibull(2.0, n) * 8   # Weibull is standard for wind
    wind_direction = np.random.vonmises(np.deg2rad(240), 2, n)  # SW dominant
    wind_direction = (np.rad2deg(wind_direction) % 360)
    temperature    = np.random.normal(26, 4, n)
    gen_frac       = np.array([_simple_power_curve(ws) for ws in wind_speed])

    return pd.DataFrame({
        "wind_speed": wind_speed,
        "wind_direction": wind_direction,
        "temperature": temperature,
        "generation_fraction": gen_frac,
    })


def get_seed_data(save_dir="data"):
    """
    Main entry point. Returns (solar_seed_df, wind_seed_df).
    Tries NASA POWER first, falls back to synthetic seed if unavailable.
    """
    os.makedirs(save_dir, exist_ok=True)

    print("Fetching Pavagada (solar) seed from NASA POWER...")
    df_pvg = fetch_nasa_power(
        lat=LOCATIONS["pavagada"]["lat"],
        lon=LOCATIONS["pavagada"]["lon"],
        params=LOCATIONS["pavagada"]["params"],
    )

    if df_pvg is not None:
        solar_seed = build_solar_seed(df_pvg)
        print(f"  Solar seed shape: {solar_seed.shape}")
    else:
        print("  Using synthetic solar seed.")
        solar_seed = make_synthetic_solar_seed()

    print("Fetching Gadag (wind) seed from NASA POWER...")
    df_gad = fetch_nasa_power(
        lat=LOCATIONS["gadag"]["lat"],
        lon=LOCATIONS["gadag"]["lon"],
        params=LOCATIONS["gadag"]["params"],
    )

    if df_gad is not None:
        wind_seed = build_wind_seed(df_gad)
        print(f"  Wind seed shape: {wind_seed.shape}")
    else:
        print("  Using synthetic wind seed.")
        wind_seed = make_synthetic_wind_seed()

    solar_seed.to_csv(f"{save_dir}/seed_solar.csv")
    wind_seed.to_csv(f"{save_dir}/seed_wind.csv")
    print(f"Seeds saved to {save_dir}/")

    return solar_seed, wind_seed


if __name__ == "__main__":
    solar_seed, wind_seed = get_seed_data()
    print("\nSolar seed sample:")
    print(solar_seed.describe())
    print("\nWind seed sample:")
    print(wind_seed.describe())