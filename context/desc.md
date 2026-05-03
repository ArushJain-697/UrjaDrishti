---

# KREDL / KSPDCL — AI Renewable Generation Forecasting
## Project Documentation & Task Reference

---

## What Is Being Built

An AI-based forecasting system that predicts solar and wind energy generation across Karnataka — at individual plant level and at cluster level — for three time horizons: day-ahead (next 24 hours), intra-day (updated every 3–4 hours), and hourly nowcast.

The system sits on top of existing SCADA infrastructure without modifying it. All data stays within Karnataka. No cloud-hosted AI is used anywhere. Every forecast comes with uncertainty ranges and a plain-language explanation of what drove the prediction.

---

## The Core Problem

Renewable generation varies with weather. Solar output drops when clouds come in. Wind output spikes and collapses with wind patterns. Grid operators need to know in advance how much generation to expect so they can plan backup sources, avoid curtailment, and keep the grid balanced.

Raw weather data alone is not enough. The relationship between weather and generation is non-linear, asset-specific, and location-dependent. A model trained naively on raw irradiance or wind speed will underperform. The system needs physics-informed features, a model that generalizes across all assets, calibrated uncertainty, and outputs that operators can actually interpret.

---

## Data

**Source:** Synthetic data generated to mimic Karnataka renewable portfolio characteristics. Real data cannot be shared or used for training.

**Generation method:** Gaussian Copula — generates correlated multivariate time series that preserves seasonal structure, diurnal patterns, and the physical relationships between weather variables and generation output.

**What gets generated:**
- Hourly solar irradiance (GHI), temperature, cloud cover for solar plants
- Hourly wind speed, wind direction for wind plants
- Corresponding generation output for each plant
- One year of history, hourly resolution
- 6 synthetic plants across 2 clusters

**Asset registry:** Each plant is described by type (solar/wind), installed capacity, technology class, geographic coordinates, tilt angle or hub height. This metadata becomes model input features.

**Edge case scenarios generated separately:** sudden cloud ramp, monsoon onset pattern, wind speed spike, sustained low irradiance. Used for stress testing only, not training.

---

## Physics Transforms

Raw weather variables are never fed directly into the model. Two physics transforms are applied first.

**For solar — Cloud Modification Factor:**
The Ineichen-Perez model computes Clear Sky Irradiance (CSI) — what irradiance would be under perfectly clear conditions at that location, time, and date. The Cloud Modification Factor (CMF) is then derived as actual GHI divided by clear-sky GHI. CMF is what enters the model instead of raw irradiance.

Why: CMF is stable, bounded between 0 and 1, and directly encodes cloud attenuation relative to theoretical maximum. A model trained on CMF generalizes across seasons and geographies far better than one trained on raw irradiance which varies enormously by time of day and time of year.

**For wind — Power Curve Transform:**
Raw wind speed is passed through the turbine class power curve to produce a theoretical generation fraction. This converts wind speed (a meteorological variable) into its expected generation equivalent before any statistical learning occurs.

Why: The relationship between wind speed and power output is cubic and non-linear with cut-in and cut-out thresholds. Letting the model learn this from scratch is wasteful and fragile. The physics transform handles it explicitly.

---

## Forecasting Model

**Architecture: Global LightGBM with two-stage correction**

A single LightGBM model trains across all plants simultaneously. Plants are not modeled separately. Each data row includes the plant's asset characteristics as features — this lets one model generalize across all asset types and geographies without retraining per plant.

**Input features:**
- Cloud Modification Factor (solar) or power curve output (wind)
- Temperature
- NWP ensemble spread (simulated variation across multiple weather model runs — encodes atmospheric uncertainty directly)
- Cyclical time encodings: hour of day, day of year encoded as sine-cosine pairs
- Asset features: capacity, type, tilt/azimuth or hub height, lat/lon as sine-cosine transforms
- Season indicator

**Two-stage setup:**
- Stage 1: Point forecast model produces primary generation prediction for each hour
- Stage 2: Residual correction model analyzes recent forecast errors (last 6 hours of actuals vs predictions) and corrects systematic bias for remaining forecast hours

The residual correction is what makes intra-day updates useful. As the day progresses and real actuals arrive, the correction model recalibrates the afternoon forecast in near real time.

**Horizons:**
- Day-ahead: runs once in late afternoon using latest NWP, produces full next-24-hour forecast
- Intra-day: runs every 3–4 hours, incorporates elapsed actuals, residual correction active
- Hourly nowcast: heavy weight on persistence for next 1–3 hours, blends with NWP beyond that

---

## Uncertainty Quantification

**Method: Conformalized Quantile Regression (CQR)**

CQR wraps the LightGBM model and produces three outputs per forecast hour: P10 (lower bound), P50 (median expected), P90 (upper bound) at 80% confidence.

CQR makes no distributional assumptions. The intervals are mathematically guaranteed to contain the actual value at the stated confidence level — this is provable, not heuristic.

**Adaptive behavior:**
- On clear sunny days: intervals narrow because conditions are stable and predictable
- During monsoon transitions or cloud ramps: intervals widen automatically
- NWP ensemble spread is an input feature, so atmospheric forecast uncertainty is baked in before CQR calibration is applied

**Operational meaning:**
- Narrow interval → tight scheduling is safe, reserve margin can be minimized
- Wide interval → hold reserve, or wait for next intra-day update before committing

**Calibration check:** On the holdout set, the 80% interval must contain the actual value approximately 80% of the time. This is verified and charted as part of evaluation.

---

## Explainability

**Method: SHAP + template-based alert generation**

SHAP (SHapley Additive exPlanations) is computed for every hourly forecast. It identifies which features pushed the prediction above or below the seasonal baseline, and by how much.

The top 3 SHAP drivers per forecast hour per plant are extracted and passed through a template mapper that converts feature-level signals into plain language.

**Example outputs:**
- "Forecast for Pavagada Block 4 is 22% below seasonal expected — cloud modification factor is the dominant driver."
- "Gadag Wind Cluster 2 forecast to peak at 14:00 — wind speed above rated threshold, high confidence interval."
- "Chitradurga solar revised down in intra-day update — temperature-driven efficiency drop compounding partial cloud cover."

No LLM is used in the prototype. Template-based generation is sufficient to demonstrate the concept. The production architecture includes an offline quantized Small Language Model (Phi-3 Mini / TinyLlama via llama.cpp) for more flexible natural language generation — this runs entirely on-premise with no internet connection.

---

## Hierarchical Reconciliation

Plant-level forecasts and cluster-level forecasts are generated independently. Without reconciliation, they will not be numerically consistent — plant forecasts summed will not match the cluster forecast. This creates contradictions across operator dashboards and destroys trust.

**Method: Minimum Trace (MinT) reconciliation**

MinT is applied as a post-hoc matrix operation after all forecasts are generated. It adjusts plant-level and cluster-level outputs simultaneously so they are mathematically consistent at every level of the hierarchy.

Plant forecasts sum exactly to cluster totals. Cluster totals aggregate exactly to regional totals. No retraining required. No architectural changes required.

---

## Evaluation

**Primary metric:** CRPS (Continuous Ranked Probability Score) — jointly evaluates point accuracy and probabilistic calibration in a single number.

**Supporting metrics:** nMAE (normalized Mean Absolute Error), nRMSE (normalized Root Mean Square Error)

**Baselines:**
- Persistence: forecast equals actual from 24 hours prior
- Climatological mean: average generation for that plant, hour, and month
- Raw NWP linear regression: no physics transforms, no asset encoding

**Targets:**
- 15–20% nMAE improvement over persistence for day-ahead solar
- 10–15% nMAE improvement over persistence for day-ahead wind

**Holdout method:** Rolling temporal holdout. No future data ever enters a training window.

**Stress tests:** Edge case scenarios (cloud ramp, monsoon onset, wind spike) are run through the model. CQR intervals should visibly widen on these events compared to calm-day baselines.

---

## Dashboard

**Tool: Streamlit**

Two views:

**Plant view** (for plant engineers): 24-hour forecast ribbon with P10/P50/P90 bands, top SHAP drivers, alert panel, actual vs forecast comparison as the day progresses.

**Cluster view** (for dispatchers): Aggregated cluster forecast, consistency with plant-level totals (MinT toggle showing before/after), cluster-level alert summary.

**Intra-day update simulation:** Button or auto-refresh that feeds in the latest actuals and triggers residual correction — forecast updates visibly for remaining hours.

---

## What the Production Architecture Adds (Beyond Prototype)

The sandbox prototype uses LightGBM. The production architecture upgrades to a Spatio-Temporal Graph Neural Network combined with a Transformer. Plants become nodes in a spatial graph with edges weighted by geographic proximity and meteorological correlation. The STGNN propagates weather signals across the graph — a cloud front moving through Pavagada sequentially affects adjacent clusters in predictable spatial patterns. The Transformer handles temporal dependencies across the 24-hour horizon.

This is documented as the roadmap. It is not prototyped in 5 days.

Similarly, the offline SLM (Phi-3 Mini via llama.cpp on edge hardware) is the production explainability layer. Not prototyped but fully specified.

---

---

## Person-Wise Responsibility

---

**Person 1 — Data & Physics**

Owns the synthetic dataset and all physics transforms. Everything in the ML pipeline depends on this work being correct. Responsible for the Gaussian Copula data generator, Ineichen-Perez clear-sky model, Cloud Modification Factor derivation, turbine power curve transform, asset registry, NWP ensemble spread simulation, cyclical time encodings, and edge case scenario generation for stress tests. Deliverable is a clean, reproducible feature matrix handed off to Person 2 by end of Day 2. On Day 5 writes the data section of the submission document.

---

**Person 2 — Forecasting Model**

Owns the core ML pipeline. Responsible for the global LightGBM model, asset encoding, two-stage point forecast plus residual correction architecture, intra-day update mechanism, and CQR uncertainty wrapping. The calibration chart showing 80% interval coverage on holdout is a critical submission artifact. On Day 5 packages the full inference pipeline as a callable function for Person 5 to wire into the dashboard. This is the most technically demanding role.

---

**Person 3 — Explainability & Reconciliation**

Owns SHAP computation, the alert template system, and MinT hierarchical reconciliation. Responsible for extracting top SHAP drivers per forecast per plant, mapping them to readable operator language across at least 8 common weather-generation scenarios, implementing MinT as a matrix operation, and producing before/after reconciliation screenshots. Also reviews alert strings with the team for operational clarity. Writes the explainability and reconciliation sections of the submission document.

---

**Person 4 — Evaluation & Stress Testing**

Owns the evaluation harness and all baseline implementations. Responsible for rolling holdout splits, nMAE/nRMSE/CRPS computation, persistence baseline, climatological mean baseline, raw NWP regression baseline, comparison table, stress test runs on edge case scenarios, season-stratified performance analysis, and CQR interval widening plots. Writes the evaluation section of the submission document. Defends the numbers during evaluator Q&A.

---

**Person 5 — Dashboard, Integration & Submission**

Owns the Streamlit dashboard, end-to-end integration, demo, and final submission package. Responsible for plant view, cluster view, P10/P50/P90 ribbon rendering, alert panel, intra-day update trigger, MinT reconciliation toggle, full end-to-end rehearsal on Day 4, 2-minute demo video recording, and compiling the final submission document from all team members' sections. The demo video should show a cloud event alert firing, an interval widening, an intra-day recalibration, and the reconciliation toggle. Most stressful role on Day 5.

---