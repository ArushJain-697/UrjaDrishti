"""L1: weather -> megawatts, with physics only (no learning).

The SAME functions turn ERA5 truth into "actual" generation and NWP forecasts into the
"physics prior". So the learned model's job is purely to correct forecast-weather error.

Watch-out (ticket #3): Open-Meteo radiation is the mean over the PRECEDING hour, so solar
position is taken at mid-hour (t - 30 min). Using t itself shifts the sun by 30 min and
creates a fake morning/evening bias of several MW.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib

from urja import config as C


def solar_geometry(index: pd.DatetimeIndex, site: C.Site) -> pd.DataFrame:
    mid = index - pd.Timedelta(minutes=30)
    loc = pvlib.location.Location(site.lat, site.lon, tz=C.TZ)
    sp = loc.get_solarposition(mid)
    cs = loc.get_clearsky(mid, model="ineichen")
    out = pd.DataFrame({
        "zenith": sp["apparent_zenith"].to_numpy(),
        "azimuth": sp["azimuth"].to_numpy(),
        "clearsky_ghi": cs["ghi"].to_numpy(),
    }, index=index)
    return out


def pv_power_mw(ghi: pd.Series, temp_c: pd.Series, site: C.Site, geom: pd.DataFrame | None = None) -> pd.Series:
    """PVWatts-style plant: GHI -> POA (Erbs + isotropic) -> cell temp -> DC -> AC clip."""
    geom = solar_geometry(ghi.index, site) if geom is None else geom
    ghi = ghi.clip(lower=0).astype(float)
    zen = geom["zenith"]
    doy = ghi.index.dayofyear
    erbs = pvlib.irradiance.erbs(ghi, zen, doy)
    dni = pd.Series(np.nan_to_num(np.asarray(erbs["dni"], float)), index=ghi.index)
    dhi = pd.Series(np.nan_to_num(np.asarray(erbs["dhi"], float)), index=ghi.index)
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=C.PV_TILT_DEG, surface_azimuth=180.0,
        solar_zenith=zen, solar_azimuth=geom["azimuth"],
        dni=dni, ghi=ghi, dhi=dhi, model="isotropic",
    )["poa_global"].fillna(0).clip(lower=0)
    t_cell = pvlib.temperature.sapm_cell(poa, temp_c, wind_speed=1.0,
                                         **pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_glass"])
    dc_mw = site.ac_mw * C.PV_DC_AC_RATIO
    pdc = pvlib.pvsystem.pvwatts_dc(poa, t_cell, pdc0=dc_mw, gamma_pdc=C.PV_GAMMA)
    ac = (pdc * 0.96).clip(lower=0, upper=site.ac_mw)          # 96% inverter + wiring, AC clipping
    ac[zen >= 90] = 0.0
    return ac.rename("mw")


def wind_power_mw(ws: pd.Series | np.ndarray, site: C.Site) -> np.ndarray:
    """Generic IEC class-II curve: cubic between cut-in and rated, flat to cut-out, 0 above."""
    v = np.asarray(ws, dtype=float)
    frac = np.clip((v**3 - C.WIND_CUT_IN**3) / (C.WIND_RATED**3 - C.WIND_CUT_IN**3), 0.0, 1.0)
    frac[(v < C.WIND_CUT_IN) | (v >= C.WIND_CUT_OUT)] = 0.0
    return frac * site.ac_mw * 0.92                             # 8% wake + electrical losses


def to_mw(weather: pd.DataFrame, site: C.Site, geom: pd.DataFrame | None = None) -> pd.Series:
    if site.kind == "solar":
        return pv_power_mw(weather["shortwave_radiation"], weather["temperature_2m"], site, geom)
    return pd.Series(wind_power_mw(weather["wind_speed_100m"], site), index=weather.index, name="mw")
