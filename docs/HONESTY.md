# Honesty inventory

What every component really is, so nobody has to ask.

| Component | What it really is | Risk if someone probes | What we say |
|---|---|---|---|
| Weather forecasts (model inputs) | **Real.** Archived ECMWF IFS 0.25°, GFS and ICON runs, the value each forecast ~24 h earlier (Open-Meteo previous-runs API, `_previous_day1`) | Lead is ~24 h, a real SLDC schedule has 14–38 h | "Real archived forecasts at ~24 h lead; real lead times would make errors somewhat larger" |
| Weather truth | **Real reanalysis.** ERA5 (Open-Meteo archive API), 0.25° grid | ERA5 is not a pyranometer or a nacelle anemometer; ERA5 and ECMWF IFS share a modelling centre | "Reanalysis truth; ECMWF may be flattered" |
| Plant generation ("actual") | **Simulated with physics** from the ERA5 weather: pvlib PVWatts-style plant (125 MWp DC / 100 MW AC, 14° tilt) and a generic IEC class-II turbine curve | No soiling, outages, curtailment, wake effects or real turbine curves | "Plant output is simulated because Karnataka SCADA is not public. The forecast error the model learns is real; plant behaviour is not" |
| Sites | Real locations (Pavagada, Koppal, Gadag/Kappatagudda, Chitradurga/Jogimatti); **modelled** 100 MW blocks | Not the real parks' nameplate | Said in README and config |
| LightGBM quantiles | Real learned model, fixed hyper-parameters, never tuned on calib/val/test | – | – |
| Conformal calibration | Real, per tier, on every 4th week of the training year | Calibration year ≠ test year (seasons shift); coverage is near target, not guaranteed | "Coverage is earned on held-out weeks and checked on a sealed year" |
| Tiers | Deterministic thresholds in `config.py`, chosen looking at the validation split | Chosen by eye, not optimised | Said in config comment |
| Schedule | Deterministic rule (P50, RED → review) | Not a cost-optimal bid | "The model never decides what gets filed" |
| Deviation cost | **Proxy**: energy outside ±10% of capacity, no rupees | Real CERC/KERC charges differ by rate, band and state | "A proxy, not a bill" |
| Validation split | Looked at many times during design | Numbers on it are optimistic by construction | Labelled "design choices were made looking at this" |
| Test year | Scored once (`results/metrics_test.json`, commit `181baa7`), the script refuses a second run | – | "Sealed, scored once" |
| Edge numbers | Measured on an Apple M4 (Arm64, 1 thread) | Not a Raspberry Pi | "Pi 5 numbers pending `scripts/bench_pi.sh`" |
| Dashboard | Replays stored predictions; no live weather pull | Not real-time | "A replay desk" |
