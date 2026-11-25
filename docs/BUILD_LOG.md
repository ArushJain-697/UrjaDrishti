# Build log (v2)

What actually happened, including what broke. Newest last.

1. **v1 audit: the baseline beat the model by 5×.** v1's evaluation reported solar nMAE 0.162 for the model
   and 0.029 for "raw NWP". The "raw NWP" baseline was a regression on the *observed* GHI of the hour being
   forecast, and the model's main feature (CMF = observed GHI / clear-sky) also used observed weather. Neither
   was a forecast. The headline "83% better than persistence" compared against the weakest baseline. v2
   was rebuilt on real archived forecasts.
2. **Data source choice.** Open-Meteo's previous-runs API gives each model's forecast from the run ~24 h
   earlier. ECMWF IFS 0.25° values are null before spring 2024, so the period starts 2024-04-01.
3. **Bug: Erbs decomposition returned ndarrays** on pvlib 0.16, so `.fillna` failed. Wrapped as Series.
4. **Rejected: a clear-sky "ceiling" as a hard gate.** ERA5-driven output exceeded the Ineichen clear-sky
   plant output in 20% of daylight hours (default turbidity is too high for these sites, plus cloud
   enhancement). Kept as a feature only; the gate is [0, capacity] and zero at night.
5. **The Flat-Band Trap found.** With one conformal correction, coverage was 0.83 in GREEN hours and 0.70–0.75
   in RED hours. Tier-conditional (Mondrian) calibration fixed it.
6. **Held-out discipline repaired.** Apr–Oct 2025 had been inspected several times while choosing tier
   thresholds, so it was relabelled *validation* and a new sealed test year (Nov 2025 – Oct 2026) was
   added before anything was scored on it.
7. **Bug: a missing forecast hour became "0 MW".** ICON has 0.3% missing hours at one site; the physics
   turned NaN irradiance into 0 MW. Now NaN propagates and the ensemble uses `nanmean`.
8. **Deadlock: LightGBM + PyTorch in one process on macOS.** Each ships its own OpenMP runtime; the first
   attempt segfaulted (exit 139), the second hung. `urja.models.common` now holds the shared helpers so the
   MLP export runs in a child process that never imports LightGBM.
9. **Negative result: int8 is slower.** Dynamic int8 quantization halved the MLP (30 → 14 KB) and kept CRPS
   within ±3%, but latency rose (21 → 26 µs per plant-day): quantize/dequantize overhead dominates a 64-unit
   network.
10. **Sealed test year scored once** (commit `181baa7`). Solar point forecast did **not** beat the NWP-ensemble
    mean; wind beat linear MOS by 15.5%. Per-tier calibration held (RED coverage 68% → 82% solar, 73% → 84%
    wind). The validation ablation said three weather models did not help; the test year said they did for
    solar. Both are reported.
