"""
Day 1 core: Gaussian Copula data generator.
Fits a GaussianCopula on NASA POWER seed data, then samples
8760 hours × 6 plants of synthetic weather + generation data.
Preserves physical correlations between weather variables.
"""

import numpy as np
import pandas as pd
import os
import warnings
warnings.filterwarnings("ignore")

from sdv.single_table import GaussianCopulaSynthesizer
from sdv.metadata import SingleTableMetadata

from asset_registry import get_registry_df

np.random.seed(42)

# Karnataka seasons by month
# 0=winter, 1=summer, 2=monsoon, 3=post-monsoon
SEASON_MAP = {
    1: 0, 2: 0,          # winter: Dec–Feb
    3: 1, 4: 1, 5: 1,    # summer: Mar–May
    6: 2, 7: 2, 8: 2, 9: 2,  # monsoon: Jun–Sep
    10: 3, 11: 3,         # post-monsoon: Oct–Nov
    12: 0,               # winter: Dec
}

# Seasonal GHI scale factors for Karnataka (relative to annual mean)
# Monsoon = strongly suppressed, summer = peak
SOLAR_SEASONAL = {0: 0.85, 1: 1.15, 2: 0.45, 3: 0.90}

# Seasonal wind scale factors
# Post-monsoon / NE monsoon = windier
WIND_SEASONAL = {0: 0.90, 1: 0.80, 2: 1.10, 3: 1.20}


# -------------------------------------------------------------------
# COPULA FITTING
# -------------------------------------------------------------------

def fit_solar_copula(solar_seed_df):
    """
    Fit a GaussianCopula on solar seed data.
    Columns expected: GHI, temperature, cloud_cover, generation_fraction
    """
    print("  Fitting solar GaussianCopula...")

    # SDV needs metadata to understand column types
    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(solar_seed_df.reset_index(drop=True))

    synthesizer = GaussianCopulaSynthesizer(metadata)
    synthesizer.fit(solar_seed_df.reset_index(drop=True))
    print("  Solar copula fitted.")
    return synthesizer


def fit_wind_copula(wind_seed_df):
    """
    Fit a GaussianCopula on wind seed data.
    Columns expected: wind_speed, wind_direction, temperature, generation_fraction
    """
    print("  Fitting wind GaussianCopula...")

    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(wind_seed_df.reset_index(drop=True))

    synthesizer = GaussianCopulaSynthesizer(metadata)
    synthesizer.fit(wind_seed_df.reset_index(drop=True))
    print("  Wind copula fitted.")
    return synthesizer


# -------------------------------------------------------------------
# DIURNAL ENVELOPE (solar only)
# -------------------------------------------------------------------

def solar_diurnal_envelope(hour, doy, lat=14.5):
    """
    Returns a multiplier [0, 1] representing the theoretical fraction
    of peak irradiance at a given hour and day of year.
    Zero at night, peaks at solar noon.
    """
    # Solar declination (degrees)
    decl = 23.45 * np.sin(np.deg2rad(360 / 365 * (doy - 81)))

    # Hour angle (degrees): 0 at solar noon
    hour_angle = 15 * (hour - 12)

    # Zenith angle
    cos_zenith = (
        np.sin(np.deg2rad(lat)) * np.sin(np.deg2rad(decl))
        + np.cos(np.deg2rad(lat)) * np.cos(np.deg2rad(decl)) * np.cos(np.deg2rad(hour_angle))
    )
    cos_zenith = np.clip(cos_zenith, 0, 1)
    return cos_zenith   # 0 when sun below horizon


# -------------------------------------------------------------------
# SOLAR PLANT DATA GENERATION
# -------------------------------------------------------------------

def generate_solar_plant(plant, solar_copula, timestamps):
    """
    Generate 8760 rows for one solar plant.
    Applies diurnal envelope + seasonal scaling on top of copula samples.
    """
    hours  = timestamps.hour.values
    doys   = timestamps.dayofyear.values
    months = timestamps.month.values

    n = len(timestamps)

    # Sample from copula — sample more than needed, we'll filter night
    # and reconstruct. Sample 2× to have buffer.
    raw = solar_copula.sample(num_rows=n * 2)

    # Clip physical bounds
    raw["GHI"]                 = raw["GHI"].clip(0, 1200)
    raw["temperature"]         = raw["temperature"].clip(15, 48)
    raw["cloud_cover"]         = raw["cloud_cover"].clip(0, 1)
    raw["generation_fraction"] = raw["generation_fraction"].clip(0, 1)

    # Take first n rows
    raw = raw.iloc[:n].reset_index(drop=True)

    records = []
    for i in range(n):
        hour  = hours[i]
        doy   = doys[i]
        month = months[i]
        season = SEASON_MAP[month]
        seasonal_factor = SOLAR_SEASONAL[season]

        diurnal = solar_diurnal_envelope(hour, doy, lat=plant["latitude"])

        if diurnal < 0.02:
            monthly_temps = {1:22,2:25,3:30,4:36,5:38,6:28,7:26,8:26,9:27,10:27,11:24,12:21}
            temp = monthly_temps[month] + np.random.normal(0, 2)
            # Nighttime — zero generation, GHI=0
            records.append({
                "timestamp":           timestamps[i],
                "plant_id":            plant["plant_id"],
                "plant_type":          "solar",
                "cluster_id":          plant["cluster_id"],
                "GHI":                 0.0,
                "temperature":         round(temp, 2),
                "cloud_cover":         raw.loc[i, "cloud_cover"],
                "wind_speed":          np.nan,
                "wind_direction":      np.nan,
                "generation_mw":       0.0,
                "capacity_mw":         plant["capacity_mw"],
                "season":              season,
            })
        else:
            # Daytime — scale GHI by diurnal × seasonal
            ghi_raw  = raw.loc[i, "GHI"]
            ghi      = ghi_raw * diurnal * seasonal_factor
            ghi      = np.clip(ghi, 0, 1200)

            cloud    = raw.loc[i, "cloud_cover"]
            # During monsoon, push cloud cover up
            if season == 2:
                cloud = np.clip(cloud + np.random.uniform(0.1, 0.4), 0, 1)

            # GHI suppressed by cloud
            ghi_actual = ghi * (1 - 0.75 * cloud)

            monthly_temps = {1:22,2:25,3:30,4:36,5:38,6:28,7:26,8:26,9:27,10:27,11:24,12:21}
            temp = monthly_temps[month] + np.random.normal(0, 2)
            # Performance ratio degrades with temperature above 25°C
            pr       = 0.75 * (1 - 0.003 * max(temp - 25, 0))
            gen_frac = np.clip(ghi_actual / 1000 * pr, 0, 1)
            gen_mw   = gen_frac * plant["capacity_mw"]

            records.append({
                "timestamp":      timestamps[i],
                "plant_id":       plant["plant_id"],
                "plant_type":     "solar",
                "cluster_id":     plant["cluster_id"],
                "GHI":            round(ghi_actual, 2),
                "temperature":    round(temp, 2),
                "cloud_cover":    round(cloud, 3),
                "wind_speed":     np.nan,
                "wind_direction": np.nan,
                "generation_mw":  round(gen_mw, 3),
                "capacity_mw":    plant["capacity_mw"],
                "season":         season,
            })

    return pd.DataFrame(records)


# -------------------------------------------------------------------
# WIND PLANT DATA GENERATION
# -------------------------------------------------------------------

def generate_wind_plant(plant, wind_copula, timestamps):
    """
    Generate 8760 rows for one wind plant.
    Applies seasonal scaling and hub-height correction.
    """
    months = timestamps.month.values
    n = len(timestamps)

    raw = wind_copula.sample(num_rows=n)
    raw["wind_speed"]     = raw["wind_speed"].clip(0, 35)
    raw["wind_direction"] = raw["wind_direction"].clip(0, 360)
    raw["temperature"]    = raw["temperature"].clip(15, 42)
    raw = raw.reset_index(drop=True)

    # Hub height correction: v_hub = v_10m * (hub/10)^alpha
    alpha = 0.143
    hub   = plant["hub_height_m"]
    height_factor = (hub / 10) ** alpha

    records = []
    for i in range(n):
        month  = months[i]
        season = SEASON_MAP[month]
        seasonal_factor = WIND_SEASONAL[season]

        ws_10m = raw.loc[i, "wind_speed"]
        ws_hub = ws_10m * height_factor * seasonal_factor
        ws_hub = np.clip(ws_hub, 0, 35)

        wd   = raw.loc[i, "wind_direction"]
        monthly_temps = {1:22,2:25,3:30,4:36,5:38,6:28,7:26,8:26,9:27,10:27,11:24,12:21}
        temp = monthly_temps[month] + np.random.normal(0, 2)

        # Apply power curve
        gen_frac = power_curve(ws_hub)
        # Add small noise only when turbine is actually producing
        # (wake effects, minor curtailment) — never below cut-in
        if gen_frac > 0:
            gen_frac = np.clip(gen_frac + np.random.normal(0, 0.008), 0, 1)
        gen_mw   = gen_frac * plant["capacity_mw"]

        records.append({
            "timestamp":      timestamps[i],
            "plant_id":       plant["plant_id"],
            "plant_type":     "wind",
            "cluster_id":     plant["cluster_id"],
            "GHI":            np.nan,
            "temperature":    round(temp, 2),
            "cloud_cover":    np.nan,
            "wind_speed":     round(ws_hub, 3),
            "wind_direction": round(wd, 1),
            "generation_mw":  round(gen_mw, 3),
            "capacity_mw":    plant["capacity_mw"],
            "season":         season,
        })

    return pd.DataFrame(records)


def power_curve(ws, cut_in=3.0, rated=12.0, cut_out=25.0):
    """Standard IEC Class II onshore turbine power curve."""
    if ws < cut_in or ws > cut_out:
        return 0.0
    elif ws >= rated:
        return 1.0
    else:
        return ((ws - cut_in) / (rated - cut_in)) ** 3


# -------------------------------------------------------------------
# MASTER GENERATOR
# -------------------------------------------------------------------

def generate_all_plants(solar_seed_df, wind_seed_df, save_dir="data"):
    """
    Fits copulas and generates 8760 × 6 plants of synthetic data.
    Returns a single DataFrame with all plants.
    """
    os.makedirs(save_dir, exist_ok=True)

    registry = get_registry_df()

    # Year of hourly timestamps — Karnataka timezone
    timestamps = pd.date_range(
        start="2023-01-01 00:00",
        periods=8760,
        freq="h",
        tz="Asia/Kolkata",
    )

    # Fit copulas once
    print("Fitting copulas on seed data...")
    solar_copula = fit_solar_copula(solar_seed_df)
    wind_copula  = fit_wind_copula(wind_seed_df)

    all_dfs = []

    for _, plant in registry.iterrows():
        print(f"  Generating data for {plant['plant_id']} ({plant['type']})...")

        if plant["type"] == "solar":
            df_plant = generate_solar_plant(plant, solar_copula, timestamps)
        else:
            df_plant = generate_wind_plant(plant, wind_copula, timestamps)

        all_dfs.append(df_plant)

    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all = df_all.sort_values(["timestamp", "plant_id"]).reset_index(drop=True)

    out_path = f"{save_dir}/raw_weather_data.csv"
    df_all.to_csv(out_path, index=False)
    print(f"\nSaved {len(df_all)} rows to {out_path}")
    print(f"Shape: {df_all.shape}")
    print(f"Plants: {df_all['plant_id'].unique()}")

    return df_all


if __name__ == "__main__":
    # Quick test without NASA fetch
    from fetch_nasa_power import get_seed_data
    solar_seed, wind_seed = get_seed_data()
    df = generate_all_plants(solar_seed, wind_seed)
    print("\nSample rows:")
    print(df.head(12).to_string())
    print("\nGeneration stats by plant:")
    print(df.groupby("plant_id")["generation_mw"].describe().round(2))