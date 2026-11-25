# UrjaDrishti v2: bible

Numbers here are pointers to the generated tables in the README, never retyped, except where a sentence
quotes one for the pitch; those come from `results/metrics_test.json`.

## 0. One line
Day-ahead renewable forecasts that know which hours they are unsure about, so a dispatcher looks at the
fifth of hours that carry three-quarters of the deviation risk.

## 1. Person, moment, cost
- **Person:** the scheduler at a Karnataka solar/wind generator (or its QCA) filing tomorrow's schedule.
- **Moment:** a monsoon afternoon where ICON says sun and GFS says storm, or a wind ramp the models time differently.
- **Cost:** energy outside the tolerance band around the schedule is charged under deviation settlement.

## 2. The trap: Flat-Band Trap
A band calibrated once on all hours is right on average and wrong where it matters: too narrow on RED hours
(68–73% coverage in the test year for an 80% band), too wide on calm ones. Fix: decide the tier from
forecast-time signals, then calibrate each tier separately (Mondrian CQR).

## 3. Positioning
| Approach | What it gives | What it lacks |
|---|---|---|
| Raw NWP → power curve | One number per hour | No uncertainty; GFS is biased by +13–19% of capacity for wind here |
| Linear MOS (classic post-processing) | Bias-corrected point | No band, no tiers |
| ML point forecast (most hackathon entries) | Lower MAE | Says nothing about which hours to distrust |
| Quantile model + one global calibration | A band | Falls into the Flat-Band Trap |
| **UrjaDrishti** | Per-hour band with tier-level coverage, deterministic schedule, RED → human | Simulated plant output (see HONESTY) |

## 4. Principle
**The model estimates; it never files.** The schedule is a fixed rule over the calibrated distribution, and
RED hours go to a person.

## 5. Ordered questions → layers (= folders)
1. What did the weather models say? `data/` (real archived runs; truth kept separate)
2. What would that weather produce? `physics/` (pvlib, power curve, same code for truth and forecast)
3. What did the models get wrong before, given this situation? `features/` + `models/` (forecast-only features, 9 quantiles)
4. Is the answer physically possible? `models/common.gate` (sorted, [0, cap], 0 at night)
5. How unsure are we, and is that honest? `uncertainty/` (tiers) + per-tier conformal
6. What do we file, and who checks? `decision/` (P50; RED → review)
7. Did it work, on data nobody tuned on? `eval/` (validation + sealed test year)
8. Can it run next to the plant? `edge/` (ONNX fp32/int8 on Arm)

## 6. Degradation ladder
- One weather model missing for an hour → ensemble uses the others (`nanmean`); never "0 MW".
- LightGBM unavailable on the device → the ONNX quantile MLP (~10% worse CRPS, see edge table).
- Too few calibration points in a tier (< 50) → that tier falls back to the global correction.

## 7. Metrics
Headline: energy outside the ±10% band vs the best operator-usable baseline; tier coverage vs 80%; CRPS vs
the 3-member NWP ensemble. Baselines: persistence, climatology, each NWP, NWP mean, linear MOS. Ablations:
global calibration, no disagreement features, one weather model, no physics prior.

## 8. Three-minute demo
| Time | Beat |
|---|---|
| 0:00–0:15 | Hook: "Tomorrow's schedule is filed tonight. One fifth of the hours carry three quarters of the deviation risk. Which fifth?" |
| 0:15–0:40 | Trap: Flat-Band toggle on "one band for all hours": RED coverage bar stops short of the 80% line |
| 0:40–1:30 | Replay desk, hardest day: three weather models fan apart, tier strip turns RED, the band widens, actual dots land inside it |
| 1:30–1:50 | Toggle to "calibrated per tier": every tier reaches the line |
| 1:50–2:20 | Judge picks any date from the dropdown; the schedule and review hours are a fixed rule they can check by eye |
| 2:20–2:45 | Proof card: test year, scored once; say the solar caveat *before* the wind number |
| 2:45–3:00 | Close: "The model estimates, it never files." + simulated-plant caveat |

## 9. Challenges
| Challenge | Answer |
|---|---|
| "Isn't this just quantile regression?" | Yes, plus the part people skip: coverage per tier, earned on held-out weeks, checked on a sealed year |
| "Is the generation real?" | No: simulated with physics from reanalysis because SCADA isn't public. The forecasts and their errors are real |
| "Does it beat the weather models?" | Wind clearly. Solar point forecast does not beat averaging the three models; the band and tiers are the value |
| "What did you try that failed?" | int8 made the edge model slower; a clear-sky ceiling gate was wrong 20% of the time; validation said three weather models didn't help, the test year said they did |
| "Why Arm / edge?" | A plant-side box can forecast with no cloud dependency: the 30 KB model runs a plant-day in microseconds on one Arm core |

## 10. Considered and rejected
- Synthetic Gaussian-copula data (v1): it can't tell you anything about real forecast error.
- Clear-sky ceiling as a hard gate (wrong 20% of the time, see BUILD_LOG #4).
- Tuning hyper-parameters on calib/val (would spend the calibration data twice).
- Twilio/SendGrid alerts, hardware diagnostics, a "war room" (v1 features that scored nothing and weren't real).

## 11. What this is NOT
Not a live system, not trained on real plant output, not a bidding optimiser, not a rupee estimate, not a
replacement for the SLDC's own forecasting.

## 12. Status
| Proven on the sealed year | Built, not field-tested | Pitch-only |
|---|---|---|
| Tier coverage; wind accuracy gain; out-of-band energy reduction | ONNX MLP on Pi 5; dashboard | Real SCADA, real lead times, live weather feed |
