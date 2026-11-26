# Honesty inventory

What every component really is, so nobody has to ask.

| Component | What it really is | Risk if someone probes | What we say |
|---|---|---|---|
| Weather forecasts (model inputs) | **Real.** Archived ECMWF IFS 0.25°, GFS and ICON runs (Open-Meteo previous-runs API). v3: for each hour, the newest run started and published before 10:00 the day before (24–48 h lead) | Publication latency is an assumed 6 h; real latency varies by model | "Real archived forecasts, held to the real filing deadline" |
| Weather truth | **Real reanalysis.** ERA5 (Open-Meteo archive API), 0.25° grid | ERA5 is not a pyranometer or a nacelle anemometer; ERA5 and ECMWF IFS share a modelling centre | "Reanalysis truth; ECMWF may be flattered" |
| Plant generation ("actual") | **Simulated with physics** from the ERA5 weather: pvlib PVWatts-style plant (125 MWp DC / 100 MW AC, 14° tilt) and a generic IEC class-II turbine curve | No soiling, outages, curtailment, wake effects or real turbine curves | "Plant output is simulated because Karnataka SCADA is not public. The forecast error the model learns is real; plant behaviour is not" |
| Sites | Real locations (dev: Pavagada, Koppal, Gadag, Chitradurga; unseen: Raichur, Kalaburagi, Bagalkot, Davanagere); **modelled** 100 MW blocks | Not the real parks' nameplate | Said in README and config |
| Measured output (Belgium) | **Real grid data** from Elia: offshore wind metered at the grid connection; Limburg solar is Elia's upscaled estimate from sampled installations | Solar "measured" is itself an estimate; one weather point represents a whole province | "Measured by the grid operator; solar is upscaled" |
| Elia's forecast | **Real professional forecast**, issued 11:00 the day before | It uses far more information than we do | "We compare against the grid operator's own forecast, and it wins" |
| Second truth | NASA POWER satellite irradiance (CERES/MERRA-2), used only for scoring | Coarse grid; it disagrees with ERA5 by ~7.5% of capacity | "Two truths, both reported" |
| LightGBM quantiles | Real learned model, fixed hyper-parameters, never tuned on calib/val/test | – | – |
| Conformal calibration | Real, per tier, on every 4th week of the training year | Calibration year ≠ test year (seasons shift); coverage is near target, not guaranteed | "Coverage is earned on held-out weeks and checked on a sealed year" |
| Tiers | Deterministic thresholds in `config.py`, chosen looking at the validation split | Chosen by eye, not optimised | Said in config comment |
| Schedule | Deterministic rule (P50, RED → review) | Not a cost-optimal bid | "The model never decides what gets filed" |
| Deviation cost | **Proxy**: energy outside ±10% of capacity, no rupees | Real CERC/KERC charges differ by rate, band and state | "A proxy, not a bill" |
| Validation split | Looked at many times during design | Numbers on it are optimistic by construction | Labelled "design choices were made looking at this" |
| v2 test year | Scored once (`results/metrics_test.json`, commit `181baa7`); now development data for v3 | – | "Superseded by v3" |
| v3 sealed slices | Unseen sites + Elia test year, scored once (`results/v3_sealed.json`, commit `d6649a5`); Nov 2026+ still sealed | Unseen sites share years with training sites | "Transfer across places, not yet across time" |
| Edge numbers | Measured on an Apple M4 laptop (1 thread) | Not a Raspberry Pi | "Pi 5 numbers pending `scripts/bench_pi.sh`" |
