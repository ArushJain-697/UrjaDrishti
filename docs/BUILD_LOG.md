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

# v3 (Tier 1)

11. **Sealed first.** `docs/V3_SEAL.md` was committed before any v3 code: 4 unseen Karnataka sites, Nov 2026+
    for later, and the Elia test year (defined before the Elia data was fetched). v2's test year is now dev data.
12. **Real filing deadline.** Each hour now uses the newest model run initialised and published (+6 h) before
    10:00 IST on the day before (11:00 Brussels for Elia): the day-1 run for 00:00–05:00 IST, the day-2 run after
    that. Lead is 24–48 h instead of ~24 h. Cost on dev data: ~8% higher nMAE, 17–30% more out-of-band energy.
13. **Bug found by the second truth: every Karnataka row was 30 minutes early (v2 included).** Open-Meteo, asked
    for `Asia/Kolkata`, shifts its UTC series by 5 h and labels it +05:30. Lining NASA POWER up against ERA5
    exposed a half-hour offset. Truth and forecasts were shifted alike, so v2's comparisons were internally
    consistent, but solar geometry was 30 min off. Everything is now fetched in UTC and converted locally.
14. **NASA POWER stamps hour-beginning.** Shifting it +1 h raises its correlation with ERA5 from 0.92 to 0.97.
15. **Solar P50, three attempts.** (a) Blend toward the raw NWP mean, weight fit on calibration weeks:
    great for Karnataka, but on Belgium it pulled the forecast toward a fleet-biased physics prior (nMAE
    4.35% -> 5.50%). (b) Let the calibration weeks also choose between that and a bias-corrected MOS anchor:
    ~6 weeks at one site picked the wrong anchor for both Belgian series. (c) **Kept:** choose anchor and weight
    from out-of-fold predictions over the whole training year (month-blocked folds). The calibration weeks
    go back to conformal calibration only.
16. **Site lat/lon removed from features** so the model can be applied to sites it never saw. lead_day
    (1 or 2) added: it is known at filing time.

# CPU benchmark and optimisation

17. **fp16 broke the wind MLP silently.** ONNX fp16 conversion of the wind student gave CRPS 0.507 (fp32: 0.049).
    A constant feature (the wind "ceiling") had std ≈ 1e-6 in the normalisation layer; in fp16 the tiny rounding
    differences between x and the mean were divided by it and overflowed. Standard deviations are now floored at 1e-2
    (`urja/models/mlp.py`). fp16 is now within 0.002 of fp32 on both technologies.
18. **lleaves needs llvmlite < 0.45** (`PassManagerBuilder` was removed). Pinned in requirements.txt. treelite's C
    backend (tl2cgen) was added as a second compiler; both give outputs identical to LightGBM.
19. **Distillation helps solar, hurts wind.** Same teacher recipe (out-of-fold LightGBM quantiles, L1 to the teacher,
    weight 1.0, not tuned). Solar students beat their plain versions at every width; wind students lost at every
    width. Kept as a per-technology result rather than forcing one recipe.
20. **Two harness bugs fixed before publishing:** the deployed-student rule only looked at distilled models, and the
    ExecuTorch int8 calibration loop ran zero batches when the calibration set equalled one batch.
