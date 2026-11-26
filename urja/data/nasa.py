"""Second, independent solar truth: NASA POWER hourly all-sky irradiance (CERES/MERRA-2 based).

Used only to check that conclusions drawn against ERA5 (an ECMWF product) are not an artefact of
ERA5 and ECMWF IFS sharing a modelling centre. Never used for training or features.
Timestamps: NASA stamps the hour's start; shifted +1 h to hour-ending (corr with ERA5 0.92 -> 0.97).
"""
from __future__ import annotations

import pandas as pd

from urja import config as C
from urja.data.fetch import _get

URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"


def fetch_nasa(site: C.Site) -> pd.DataFrame:
    path = C.RAW_DIR / f"nasa_{site.plant_id}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    frames = []
    for start, end in (("20240401", "20241231"), ("20250101", "20251231"), ("20260101", "20261031")):
        p = dict(parameters="ALLSKY_SFC_SW_DWN,T2M", community="RE", longitude=site.lon, latitude=site.lat,
                 start=start, end=end, format="JSON", **{"time-standard": "UTC"})
        d = _get(URL, p)["properties"]["parameter"]
        df = pd.DataFrame(d)
        df.index = pd.to_datetime(df.index, format="%Y%m%d%H", utc=True)
        frames.append(df)
    df = pd.concat(frames).replace(-999.0, float("nan"))
    df.index = df.index + pd.Timedelta(hours=1)    # NASA stamps hour-beginning; we use hour-ending
    df = df.rename(columns={"ALLSKY_SFC_SW_DWN": "shortwave_radiation", "T2M": "temperature_2m"})
    df.index.name = "time"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df
