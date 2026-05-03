---

# Deep Dive — Each Person's Exact Work, Tools & Resources

---

## Person 1 — Data & Physics

**The job in one line:** Create the dataset that the entire project runs on, and make sure the weather-to-generation relationship is physically correct before any ML touches it.

---

**Day 1 — Synthetic Data Generation**

The goal is to generate one year of hourly data for 6 synthetic plants. Two solar plants in one cluster (think Pavagada region), two wind plants in another cluster (think Gadag region), and two mixed to show generalization.

Use a Gaussian Copula for this. The reason is that solar irradiance, temperature, cloud cover, and generation output are correlated — on a hot clear day all of them move together. A Copula preserves these correlations when generating synthetic data. Do not generate each variable independently — that produces physically impossible combinations like high irradiance with zero generation.

The library to use is `copulas` from MIT's DataCopilot team or `sdv` (Synthetic Data Vault). SDV is more beginner friendly. Install via pip. Fit the copula on a small seed dataset — even publicly available Indian solar irradiance data from NASA POWER is enough to get the correlation structure right, then scale up to a full synthetic year.

NASA POWER website (power.larc.nasa.gov) gives free historical irradiance, temperature, and wind data for any lat/lon on earth. Pull data for Pavagada coordinates (14.5°N, 77.2°E) and Gadag coordinates (15.4°N, 75.6°E) as the seed. This is public data, not Karnataka SCADA data, so there are no restrictions.

For the asset registry, create a simple CSV or dictionary with these fields per plant: plant_id, type (solar/wind), capacity_mw, latitude, longitude, tilt_angle (solar) or hub_height_m (wind), technology_class (crystalline silicon or HAWT), cluster_id. Six rows, hardcoded is fine.

---

**Day 2 — Physics Transforms**

This is the most important technical work in the entire project. Spend the full day on it.

**Ineichen-Perez Clear Sky Model:**
The library is `pvlib`. It is the industry standard Python library for solar energy modeling. Install via pip. It has a direct implementation of the Ineichen-Perez model.

What to do: for every hour in the synthetic dataset, compute Clear Sky GHI using pvlib's `clearsky.ineichen()` function. It takes location (lat, lon, altitude), time (pandas DatetimeIndex), and a Linke turbidity factor. Linke turbidity values for Karnataka are around 3.0 to 4.5 depending on season — use 3.5 as a baseline, or pull monthly values from the SoDa database (soda-pro.com, free registration).

Then compute Cloud Modification Factor: CMF = actual_GHI / clear_sky_GHI. Clip between 0 and 1. This single number encodes how much of the theoretically available solar energy actually reached the panel. This is the feature that goes into the model, not raw GHI.

pvlib documentation is at pvlib.readthedocs.io — excellent docs with worked examples.

**Turbine Power Curve Transform:**
Wind turbines have a characteristic curve: below cut-in speed (~3 m/s) they produce nothing, between cut-in and rated speed power scales roughly as the cube of wind speed, at rated speed they hit maximum output, above cut-out speed (~25 m/s) they shut down for safety.

Implement this as a lookup function. Take wind speed as input, return generation fraction (0 to 1). Use a standard IEC Class II onshore wind turbine curve — these are publicly available. The Wind Power website (thewindpower.net) has power curves for almost every turbine model. Pick a Suzlon or GE turbine common in Karnataka.

Do not use a smooth mathematical approximation — use the actual tabulated curve values and interpolate between them with numpy.interp. This matters for accuracy at the edges.

---

**Day 3 — NWP Ensemble Spread and Time Encodings**

NWP ensemble spread means: in the real world, weather forecasting models are run multiple times with slightly different initial conditions, and the spread across those runs tells you how uncertain the atmosphere is. On a clear stable day all runs agree. Before a monsoon front they diverge wildly.

Simulate this by taking the synthetic wind speed and irradiance and adding 5 slightly perturbed versions of each (add Gaussian noise with standard deviation proportional to the variable's recent variance). Then compute the standard deviation across those 5 runs. That standard deviation is the ensemble spread feature. High spread = high atmospheric uncertainty = model should produce wide intervals.

For cyclical time encodings: hour of day and day of year should never enter a model as raw integers (hour=23 is not "close to" hour=0). Encode them as sin/cos pairs:
- hour_sin = sin(2π × hour / 24)
- hour_cos = cos(2π × hour / 24)
- doy_sin = sin(2π × day_of_year / 365)
- doy_cos = cos(2π × day_of_year / 365)

This ensures temporal continuity at midnight and at year end.

---

**Day 4 — Edge Case Scenario Generation**

Generate four specific stress scenarios as separate test datasets, not part of the training data:

Cloud ramp: take a clear afternoon and insert a sharp CMF drop from 0.9 to 0.2 over 2 hours, then recovery. This simulates a fast-moving cloud front.

Monsoon onset: simulate 10 consecutive days where CMF stays below 0.3 all day and temperature drops 5 degrees below seasonal norm.

Wind ramp: take a moderate wind day and insert a spike from 8 m/s to 22 m/s over 3 hours (approaching cut-out).

Sustained low irradiance: a week where CMF averages 0.15 — deep monsoon conditions.

These four scenarios are handed to Person 4 for stress testing.

---

**Day 5 — Documentation and Support**

Write the data section of the submission document: explain why Gaussian Copula was used, what the physics transforms do and why they matter, and what the synthetic data preserves about Karnataka-specific patterns. Be available for Person 2 and Person 5 if they hit data-related bugs.

---

**Tools and Resources Summary for Person 1:**
- pvlib (pip install pvlib) — pvlib.readthedocs.io
- sdv / copulas (pip install sdv) — docs.sdv.dev
- NASA POWER data portal — power.larc.nasa.gov
- SoDa database for Linke turbidity — soda-pro.com
- The Wind Power turbine database — thewindpower.net
- numpy, pandas (standard)
- Karnataka geographic reference: Pavagada Solar Park (14.5°N, 77.2°E), Gadag Wind Farm (15.4°N, 75.6°E)

---

---

## Person 2 — Forecasting Model

**The job in one line:** Build the brain of the system — the model that takes physics-transformed weather features and predicts generation with calibrated uncertainty.

---

**Day 1 — Project Skeleton**

Before Person 1 finishes, set up the full ML pipeline skeleton so that when the feature matrix arrives, training starts immediately.

Create a Python project with this structure: a data loader module that reads Person 1's output CSV, a feature engineering module (just passthrough for now), a model module with a train() and predict() function stub, an evaluation module with nMAE/nRMSE/CRPS stubs, and a main.py that calls them in sequence.

Install LightGBM (pip install lightgbm). Also install scikit-learn, numpy, pandas, matplotlib, and mapie (pip install mapie — this is the CQR library).

Read the LightGBM documentation on its Python API, specifically the `LGBMRegressor` and the `train()` API with early stopping. lightgbm.readthedocs.io.

Run LightGBM on the California Housing dataset from sklearn just to verify the pipeline works end to end before real data arrives.

---

**Day 2 — Global Model Training**

When Person 1 hands off the feature matrix, the schema will be: one row per plant per hour, with columns for CMF or power curve output, temperature, ensemble spread, time encodings, and asset features.

The key design decision is the global model: do not train one model per plant. Train one model on all plants together. The asset features (capacity, type, tilt, lat/lon sin/cos) tell the model which plant it is looking at. This is called a "global" or "cross-sectional" model and it generalizes much better than per-plant models, especially for new assets.

LightGBM hyperparameters to start with: n_estimators=500, learning_rate=0.05, num_leaves=63, min_child_samples=20, subsample=0.8, colsample_bytree=0.8. Use early stopping with a 10% validation split. These are reasonable starting points — tune if time permits on Day 3.

The train/validation/test split must be temporal — never shuffle. Take the last 2 months as test, the 2 months before that as validation, everything else as training. Shuffling would leak future information into the past.

---

**Day 3 — Two-Stage Residual Correction**

The residual correction is what makes intra-day updates work.

Stage 1 is the model trained on Day 2 — it produces point forecasts for all 24 hours.

Stage 2 is a second LightGBM model that takes as input: the Stage 1 forecast error from the last 6 hours (actual minus predicted for elapsed hours), the hour of day, the asset features, and the current CMF or wind speed. It predicts the likely error for the remaining hours of the day.

At inference time: run Stage 1 to get the full 24-hour forecast. As actuals arrive (simulated in the prototype), compute recent errors, run Stage 2 to get error corrections, and add them to the Stage 1 output for remaining hours.

This is the intra-day recalibration. Test it by simulating: take a full day, pretend it's 12:00, feed in the morning actuals, run Stage 2, see if the afternoon forecast improves. It should. If it doesn't, check that the residual features are informative.

---

**Day 4 — Conformalized Quantile Regression**

CQR is implemented using the MAPIE library (Model Agnostic Prediction Interval Estimator). It is purpose-built for this.

The approach: use `MapieQuantileRegressor` from mapie. It wraps LightGBM and produces calibrated prediction intervals. The calibration step requires a separate calibration dataset — use 3 months of held-out data that was not used for training.

```python
from mapie.quantile_regression import MapieQuantileRegressor
mapie = MapieQuantileRegressor(lgbm_model, method="quantile", cv="split", alpha=0.2)
mapie.fit(X_train, y_train, X_calib=X_calib, y_calib=y_calib)
y_pred, y_pis = mapie.predict(X_test)
```

y_pis contains the P10 and P90 bounds. P50 comes from the base model prediction.

The calibration verification: compute coverage = fraction of test samples where actual falls between P10 and P90. It should be approximately 0.80. Plot this per plant and per season. Save these plots — they are a key submission artifact proving the uncertainty layer works.

MAPIE documentation: mapie.readthedocs.io. Very well documented with examples specifically for time series.

---

**Day 5 — Inference Packaging**

Package the full pipeline as a single callable:

```python
def get_forecast(current_features_df, recent_actuals_df=None):
    # returns dataframe with columns: plant_id, hour, p50, p10, p90
```

If recent_actuals_df is provided, the residual correction runs. If not, Stage 1 only. Person 5 calls this function from the Streamlit dashboard. Make sure it runs in under 5 seconds for the demo — LightGBM inference is fast, this should not be a problem.

Fix any bugs Person 5 finds during dashboard integration.

---

**Tools and Resources Summary for Person 2:**
- LightGBM — lightgbm.readthedocs.io
- MAPIE for CQR — mapie.readthedocs.io
- scikit-learn — scikit-learn.org
- Towards Data Science articles on global forecasting models (search "global forecasting model LightGBM")
- Rob Hyndman's forecasting textbook free online — otexts.com/fpp3 (conceptual foundation for forecast evaluation and residual correction)
- Kaggle M5 competition solutions — many use global LightGBM with similar asset encoding tricks, good reference implementations

---

---

## Person 3 — Explainability & Reconciliation

**The job in one line:** Make the model's predictions understandable to a control room operator, and make sure plant and cluster numbers never contradict each other.

---

**Day 1 — SHAP Setup and Alert Template Design**

Install shap (pip install shap). Read the SHAP documentation at shap.readthedocs.io, specifically the TreeExplainer section — this is the fast SHAP implementation for tree-based models like LightGBM and it runs in seconds even on large datasets.

On Day 1 the real model does not exist yet. Use the toy LightGBM that Person 2 is testing on California Housing to get SHAP working end to end. The workflow is:

```python
import shap
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
shap.summary_plot(shap_values, X_test)
```

Run it, understand what it outputs, make sure the waterfall plot works.

Then design the alert template system on paper. List every feature that will be in the model: CMF, wind_power_fraction, temperature, ensemble_spread, hour_sin, hour_cos, capacity, tilt, etc. For each feature write what it means when it is the top positive SHAP driver and what it means when it is the top negative SHAP driver. This is your template map. There are about 12–15 features so you will have roughly 24–30 template strings. Write them in plain language as if explaining to a non-technical operator.

Examples:
- CMF top negative driver → "Forecast reduced due to cloud cover — irradiance significantly below clear-sky baseline."
- ensemble_spread top positive driver → "High atmospheric uncertainty detected — prediction interval is wider than usual."
- temperature negative driver → "Module temperature above optimal range — thermal efficiency loss expected."
- wind_power_fraction positive driver → "Wind speed approaching rated threshold — cluster forecast near peak capacity."

---

**Day 2 — SHAP on Real Model**

When Person 2 has a trained model, run SHAP TreeExplainer on it. Extract for every row in the test set: the top 3 features by absolute SHAP value and their direction (positive or negative contribution relative to baseline).

Build the template mapper function:

```python
def generate_alert(plant_id, hour, top_shap_features):
    # top_shap_features is a list of (feature_name, shap_value) tuples
    # returns a plain language string
```

The function looks at the top driver and its sign, picks the matching template, fills in the plant name and any relevant numbers (percentage deviation, specific values), and returns a string.

Test on 20–30 forecast hours manually. Read the outputs out loud. If they sound like something a machine generated rather than something a human would say, rewrite the templates. The goal is that an operator reads the alert and immediately knows what to do.

---

**Day 3 — MinT Reconciliation**

This requires understanding the hierarchical structure. There are 6 plants in 2 clusters. Plant 1, 2, 3 belong to Cluster A. Plants 4, 5, 6 belong to Cluster B. The model produces forecasts independently for all 6 plants and for both clusters. The problem: Plant 1 forecast + Plant 2 forecast + Plant 3 forecast will not equal the Cluster A forecast. MinT fixes this.

MinT (Minimum Trace reconciliation) is implemented in the `statsforecast` library or can be implemented manually. The manual implementation is actually straightforward for a small hierarchy.

Install statsforecast (pip install statsforecast) and hierarchicalforecast (pip install hierarchicalforecast). The hierarchicalforecast library has a direct MinT implementation.

The summing matrix S encodes the hierarchy: it maps base-level plant forecasts to all levels including cluster and total. MinT finds adjustments to all forecasts that minimize total variance while satisfying the summation constraints exactly.

```python
from hierarchicalforecast.methods import MinTrace
from hierarchicalforecast.core import HierarchicalReconciliation

hrec = HierarchicalReconciliation(reconcilers=[MinTrace(method='mint_shrink')])
reconciled = hrec.reconcile(Y_hat_df, Y_df, S, tags)
```

The hierarchicalforecast documentation has a complete worked example with exactly this structure. nixtla.github.io/hierarchicalforecast.

Produce the proof: before reconciliation, sum Plant 1+2+3 forecasts and compare to Cluster A forecast — they will differ. After reconciliation, they match exactly. Save these two numbers side by side as a table — it is a strong demo moment.

---

**Day 4 — Alert Review and Submission Content**

Run the full alert generation across all 6 plants for a full 24-hour forecast period. You will get roughly 144 alerts (6 plants × 24 hours). Read through them. Flag any that sound wrong, repetitive, or confusing. Fix the templates.

Also run alerts on the stress test scenarios from Person 1. The cloud ramp scenario should produce alerts that detect the cloud event. The wind ramp should produce alerts about the wind speed crossing threshold. If the templates miss these, add specific templates for rapid CMF change or ensemble spread spike.

Create 5–6 "showcase" alerts — the most informative, most readable outputs — and send them to Person 5 to display prominently in the dashboard demo.

Write the explainability and reconciliation sections of the submission document.

---

**Day 5 — Support and Documentation**

Be available for Person 5 during dashboard integration. The SHAP pipeline and alert generator need to be called from the dashboard — make sure the API is clean, fast, and does not crash on edge cases. If the dashboard shows an unexpected plant or hour, the alert generator should return a sensible default rather than throwing an error.

---

**Tools and Resources Summary for Person 3:**
- SHAP library — shap.readthedocs.io (read the TreeExplainer section specifically)
- hierarchicalforecast by Nixtla — nixtla.github.io/hierarchicalforecast (MinT implementation with worked examples)
- statsforecast — nixtla.github.io/statsforecast
- Christoph Molnar's Interpretable ML Book (free online) — christophm.github.io/interpretable-ml-book (chapter on SHAP is excellent conceptual background)
- Rob Hyndman's hierarchical forecasting chapter — otexts.com/fpp3/reconciliation.html (explains MinT mathematically)

---

---

## Person 4 — Evaluation & Stress Testing

**The job in one line:** Prove objectively that the system works better than simple alternatives, and prove that the uncertainty layer behaves correctly under difficult conditions.

---

**Day 1 — Evaluation Harness**

Build the full evaluation framework before any model results exist. This way it is ready the moment Person 2 produces forecasts.

**Rolling temporal holdout:** The test set is the last 2 months of synthetic data. The validation set is the 2 months before that. Training is everything before that. Never shuffle.

**Metrics to implement:**

nMAE (normalized Mean Absolute Error): mean absolute error divided by the mean of actual values. This normalizes across plants of different capacities.

nRMSE (normalized Root Mean Square Error): same normalization. Penalizes large errors more than nMAE.

CRPS (Continuous Ranked Probability Score): evaluates the full probability distribution, not just the point forecast. A forecast that says "I'm 80% confident between 40 and 80 MW" gets scored on how well-calibrated that interval is. Lower CRPS is better.

Implement CRPS using the `properscoring` library (pip install properscoring). It has a `crps_gaussian` and `crps_ensemble` function. Use `crps_ensemble` which is more general.

Also implement coverage: for each confidence level (80%, 90%), what fraction of actuals fall within the predicted interval. Should match the stated confidence level closely.

Build a summary function that takes model predictions and actuals and returns a dictionary with all metrics, broken down by plant, by hour of day, and by season.

---

**Day 2 — Baseline Implementations**

Three baselines, implemented independently of Person 2's model.

**Persistence baseline:** For day-ahead forecasting, the forecast for tomorrow hour H equals the actual generation at hour H from 24 hours ago. This is the dumbest possible forecast and surprisingly hard to beat. Implement it as a simple 24-hour lag on the actuals.

**Climatological mean baseline:** For each plant, each hour of day, and each month, compute the average historical generation from the training set. The forecast for any future hour is that average. This captures seasonal and diurnal patterns but nothing else.

**Raw NWP linear regression baseline:** Take the raw weather features (GHI, temperature, wind speed) without any physics transforms and without any asset encoding. Train a separate linear regression per plant. This baseline specifically tests whether the physics transforms and global model add value — and they should.

Run all three on the test set and compute all metrics. Save results. These are the comparison rows in the final evaluation table.

---

**Day 3 — Model vs Baseline Comparison**

When Person 2 has the full model running with CQR, run it on the same test set and compute all the same metrics.

Build the comparison table:

| Model | nMAE Solar | nMAE Wind | nRMSE Solar | nRMSE Wind | CRPS |
|---|---|---|---|---|---|
| Persistence | | | | | |
| Climatological | | | | | |
| Raw NWP LR | | | | | |
| LightGBM (ours) | | | | | |

Target: 15–20% nMAE improvement over persistence for solar, 10–15% for wind.

If the numbers are not hitting target, diagnose: is the physics transform working? Is the asset encoding helping? Run ablation tests — model without CMF (use raw GHI), model without asset features, model without residual correction. Each ablation shows what each component contributes. Include this in the submission doc as it demonstrates depth of understanding.

---

**Day 4 — Stress Testing and CQR Validation**

Take the four edge case scenarios from Person 1 (cloud ramp, monsoon onset, wind ramp, sustained low irradiance) and run them through the full model pipeline including CQR.

What to verify and plot:

1. On the cloud ramp scenario: the P90-P10 interval width should increase during and after the cloud front arrives. Plot interval width over time and mark where the cloud event is. The widening should be visible.

2. On the monsoon onset scenario: point forecast accuracy will be lower (monsoon is hard), but CQR intervals should be wider to compensate. The coverage metric should still hold — actuals should still fall within the 80% interval roughly 80% of the time.

3. On the wind ramp scenario: the uncertainty interval should widen as wind speed approaches cut-out threshold. Generation becomes unpredictable near the turbine's operating limits.

4. On calm clear days (not a stress scenario but the contrast case): intervals should be narrow. A plot showing narrow intervals on a clear day next to wide intervals on a cloud ramp day is visually striking and tells the story.

Also run season-stratified evaluation: compute nMAE separately for summer months (March-May), monsoon (June-September), post-monsoon (October-November), winter (December-February). The model should hold up across all seasons — if monsoon performance is much worse, flag it.

---

**Day 5 — Final Evaluation Report**

Compile everything into the evaluation section of the submission document:

- Comparison table with all models and baselines
- Calibration chart (coverage vs stated confidence level)
- Interval width comparison: calm day vs stress scenarios
- Season-stratified performance table
- Ablation results if time permitted

During the presentation, this person defends the numbers. Anticipate evaluator questions: Why is monsoon accuracy lower? How were the baselines implemented? What does CRPS mean? Why rolling holdout instead of random split? Prepare one-sentence answers for each.

---

**Tools and Resources Summary for Person 4:**
- properscoring (pip install properscoring) — for CRPS computation
- scikit-learn metrics — for MAE, RMSE
- matplotlib and seaborn — for all plots
- pinball loss / quantile loss documentation in scikit-learn — for understanding quantile evaluation
- Tilmann Gneiting's paper "Strictly Proper Scoring Rules, Prediction, and Estimation" — foundational reference for CRPS (Google Scholar, free PDF available)
- Kaggle M5 forecasting competition writeups — practical examples of how to evaluate probabilistic forecasts correctly

---

---

## Person 5 — Dashboard, Integration & Submission

**The job in one line:** Build what the evaluators actually see, make everything work together, and own the demo.

---

**Day 1 — Streamlit Skeleton**

Set up the Streamlit app from scratch. Install Streamlit (pip install streamlit), plotly (pip install plotly), and pandas.

Create the app with two tabs using `st.tabs(["Plant View", "Cluster View"])`. Inside each tab, put placeholder text and hardcoded dummy charts. The goal is to have a running app by end of Day 1 that looks like the real thing even if all data is fake.

For the forecast ribbon chart: use Plotly's `go.Figure` with `add_trace` for a line chart (P50) and `add_trace` with fill='tonexty' for the P10-P90 shaded band. This is the signature visual of the dashboard. Get it working with dummy data today so no time is lost on Plotly syntax later.

Read the Streamlit documentation at docs.streamlit.io, specifically the layout section (columns, tabs, sidebar) and the session state section (you will need session state to manage the intra-day update simulation).

---

**Day 2 — First Real Data Integration**

Person 2 will have a rough first model output by end of Day 2. Even if it is not the final version, wire it in.

The dashboard calls Person 2's inference function, gets back a dataframe with plant_id, hour, p50, p10, p90, and renders it. Do not wait for a perfect model — get real numbers flowing through the dashboard as early as possible.

Also wire in Person 3's alert generator. For a given plant and set of SHAP values, it returns a string. Display these strings in a sidebar panel or below the chart. Even if they look rough, having them appear in the dashboard is important for the Day 4 rehearsal.

For the intra-day update simulation: use `st.button("Simulate intra-day update")`. When clicked, it sets a Streamlit session state variable `hours_of_actuals = 6`, re-calls the inference function with that parameter (which triggers Person 2's residual correction), and rerenders the chart. The P10-P90 band should visibly narrow for the upcoming hours if the correction model is working well on a clear day scenario.

---

**Day 3 — Full Feature Integration**

Wire in every component:

Plant view should show: 24-hour P10/P50/P90 forecast ribbon, actual vs forecast overlay for elapsed hours, top 3 SHAP drivers as a small horizontal bar chart below the main chart, alert panel on the right with the current alert string from Person 3, plant metadata (capacity, type, cluster) in a sidebar.

Cluster view should show: aggregated cluster forecast with P10/P50/P90, individual plant breakdown as stacked bars, the MinT reconciliation toggle — when toggled OFF it shows the raw plant sum vs raw cluster forecast (they will differ), when toggled ON it shows the reconciled versions (they match exactly). This toggle is a strong demo moment. Label it clearly: "Hierarchical consistency: OFF / ON".

Add a plant selector dropdown to the plant view so evaluators can switch between all 6 plants. Make sure all 6 work.

---

**Day 4 — Full Rehearsal**

Run the complete demo scenario from start to finish with the whole team present:

1. Open the dashboard. Show Cluster A plant view for Plant 1.
2. Explain the P10/P50/P90 ribbon. Show a calm clear day — narrow intervals.
3. Switch to the cloud ramp scenario (load Person 1's stress test data). Show intervals widening. Show the alert firing: "Forecast reduced due to cloud cover."
4. Click "Simulate intra-day update" — feed in 6 hours of morning actuals. Show the afternoon forecast recalibrating. If Person 2's residual correction is working, the P50 line will shift and the interval may narrow.
5. Switch to Cluster view. Show the reconciliation toggle OFF — plant sum does not match cluster forecast. Toggle ON — they now match exactly.
6. Show Person 4's evaluation table — the model beats all three baselines.

Time this. It should be under 2 minutes for the video. Fix whatever does not work. Today is the last chance to fix bugs.

---

**Day 5 — Video, Document, Submit**

Record the 2-minute walkthrough video using any screen recording software — OBS Studio (free, obsproject.com), Loom (loom.com, free tier), or even QuickTime on Mac. Practice the script twice before recording. Speak clearly and point to what is happening on screen.

Compile the submission document. Collect the written sections from each person:
- Person 1: data and physics section
- Person 2: model architecture section
- Person 3: explainability and reconciliation section
- Person 4: evaluation section
- Write yourself: system architecture overview, dashboard description, and the production roadmap section covering STGNN and offline SLM

The production roadmap section is important. Frame STGNN and offline SLM as deliberate architectural decisions for the production system, not things that were forgotten. Explain what they add, why they were not prototyped in 5 days, and what the migration path looks like. Evaluators reward honest scoping combined with genuine architectural ambition.

Submit everything: codebase (GitHub link), submission document (PDF), demo video (YouTube unlisted link or direct file).

---

**Tools and Resources Summary for Person 5:**
- Streamlit — docs.streamlit.io (layout, session state, charts sections are most important)
- Plotly Python — plotly.com/python (specifically filled area charts for confidence bands and bar charts for SHAP)
- OBS Studio for screen recording — obsproject.com (free)
- Loom for easy screen recording — loom.com
- GitHub for code submission — make sure the repo has a clear README with setup instructions and a requirements.txt
- Streamlit sharing (share.streamlit.io) — free hosting for Streamlit apps, useful if a live demo link is required instead of a video

---

**One final note across all five:** The project wins not because it is the most complex submission but because it is the most complete. A working dashboard that shows uncertainty-aware forecasts updating intra-day, alerts that explain the model's reasoning, and plant numbers that add up to cluster numbers — that combination is what most teams will not have. Build the complete thing, not a half-built sophisticated thing.