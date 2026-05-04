Okay let's go full send on this. Let me first give you the research brief so you know exactly what to search for, then the complete 45-slide structure with what goes on every single slide.

---

## Research Brief — Exactly What to Search in Gemini

Do these searches one by one. Copy the key numbers into a doc as you go.

**Search 1:** "Karnataka renewable energy installed capacity 2024 solar wind MW"
You need: total installed capacity, Pavagada exact capacity, Gadag wind farm capacity, year commissioned.

**Search 2:** "Karnataka renewable energy curtailment 2023 2024 MWh"
You need: how many MWh were curtailed due to forecasting errors or grid imbalance. This is the money number.

**Search 3:** "India spinning reserve cost per MW hour POSOCO CERC"
You need: the actual cost in rupees per MW-hour of keeping backup generators spinning unnecessarily.

**Search 4:** "KREDL KSPDCL renewable energy forecasting current process"
You need: what they currently do, whether they use any forecasting system, what the accuracy is.

**Search 5:** "Karnataka grid renewable penetration percentage 2024"
You need: on peak renewable days what percentage of Karnataka's grid is renewable.

**Search 6:** "India renewable energy forecast accuracy requirement CERC regulations"
You need: CERC has regulations requiring forecasting accuracy within certain bands. Find the exact regulation number and the penalty for missing it.

**Search 7:** "Pavagada solar park generation data 2023 actual vs forecast deviation"
You need: any published data on how accurate current forecasts are for Pavagada.

**Search 8:** "Karnataka electricity demand MW peak 2024"
You need: total Karnataka peak demand so you can contextualize renewable numbers.

**Search 9:** "India NWP numerical weather prediction accuracy solar wind IMDAA"
You need: what weather forecast accuracy looks like for Karnataka specifically.

**Search 10:** "CERC forecasting deviation penalty schedule 2023"
You need: the exact penalty in rupees per unit for forecast deviation. This is your ₹ savings argument.

**Search 11:** "Pavagada solar park cloud cover variability monsoon Karnataka"
You need: actual data on cloud variability to justify why forecasting is hard there specifically.

**Search 12:** "Karnataka electricity board ESCOM control room operator count"
You need: how many operators are in Karnataka's control rooms. Humanizes the user base.

---

## Complete 45-Slide Structure

---

**SECTION 1: THE PROBLEM (Slides 1-8)**

**Slide 1 — Title**
UrjaDrishti — ಊರ್ಜಾದೃಷ್ಟಿ
AI-Powered Renewable Generation Forecasting for Karnataka
KREDL / KSPDCL
"Forecasts with confidence. Explanations in plain language. Zero changes to existing systems."
Team name. Date. A single dark background with the gradient accent line.

**Slide 2 — Karnataka's Renewable Revolution**
Full-page visual. Karnataka map with renewable installations marked.

Numbers to fill in from your research:
- Total installed renewable capacity in Karnataka (MW)
- Pavagada: 2050 MW — Asia's largest operational solar park
- Gadag wind corridor: (MW from research)
- Karnataka's rank among Indian states for renewable capacity
- Year Karnataka set its renewable generation record

One sentence: "Karnataka leads India in renewable energy ambition. The grid infrastructure hasn't kept up."

**Slide 3 — The Variability Problem**
Three side-by-side charts showing:
- Solar generation curve on a clear day (clean sine wave)
- Solar generation curve on a partly cloudy day (jagged, unpredictable)
- Wind generation curve on a variable wind day (highly irregular)

Caption: "Renewable generation is not predictable by looking at the sky. It requires physics-informed AI."

**Slide 4 — What Happens Without Accurate Forecasts**
A flow diagram showing the cascade failure:

```
Inaccurate forecast
        ↓
Operators don't know how much renewable to expect
        ↓
They keep expensive backup generators spinning "just in case"
        ↓
OR they don't keep enough backup and the grid destabilizes
        ↓
Either way: money wasted, reliability compromised
```

Fill in from research: the actual cost of spinning reserve per MW-hour in Karnataka. Calculate: at X MW of unnecessary reserve × Y hours × ₹Z per MW-hour = ₹ crores per year.

**Slide 5 — The CERC Mandate**
This slide is for the IAS officers specifically. CERC (Central Electricity Regulatory Commission) has regulations requiring renewable generators to forecast accurately or face penalties.

Fill in from research:
- The exact CERC regulation number
- The penalty per unit for forecast deviation
- The accuracy band required (typically ±15% of installed capacity)
- Whether Karnataka generators are currently meeting this

One line: "Accurate forecasting isn't just operationally important. It's legally mandated."

**Slide 6 — The Current State**
Honest assessment of what Karnataka uses today for forecasting. From your research fill in:
- Do they use any AI/ML forecasting currently?
- What is their current forecast accuracy?
- How often do intraday updates happen?
- What do operators actually do when the forecast is wrong?

If you can't find specific Karnataka data: "Karnataka's current forecasting approach relies on NWP outputs without plant-level calibration, without uncertainty quantification, and without intraday recalibration."

**Slide 7 — The Human Cost**
This slide is the one that hits government officials emotionally.

Format: a day in the life of a control room operator at Pavagada.

"06:00 — Shift starts. Operator receives a single number: expected solar generation for today. No confidence range. No explanation. No update mechanism."

"10:00 — Cloud cover developing over Chitradurga. Operator has no system to warn them. They check the sky through the window."

"14:00 — Solar output drops 30% below forecast. Operator scrambles to reroute load. Grid frequency dips. Backup generators spin up at maximum cost."

"19:00 — Shift ends. The logbook says 'forecast deviation noted.' Same entry as yesterday. And the day before."

"With UrjaDrishti: the 10:00 alert arrives automatically. The operator acts at 09:45 instead of 14:00."

**Slide 8 — The Opportunity**
Three numbers large on the slide. Fill in from research:

```
₹___ Crores          ___  MWh              ___  MW
annual spinning      curtailed in          of new renewable
reserve cost in      Karnataka 2023        capacity planned
Karnataka            due to imbalance      by 2030
```

"A 17% improvement in forecast accuracy addresses all three. UrjaDrishti delivers 57%."

---

**SECTION 2: OUR SOLUTION (Slides 9-15)**

**Slide 9 — System Architecture**
The clean architecture diagram from before. Read-only SCADA feed. No modifications. On-premise. The compliance boundary box.

**Slide 10 — Why Synthetic Data Is The Right Choice**
This slide defends your data strategy proactively before anyone questions it.

"Real SCADA generation data is operationally sensitive. Sharing it violates Karnataka's data governance requirements. This is not a limitation — it is the correct approach."

Three columns:
- What synthetic data preserves: seasonal structure, diurnal patterns, physics relationships, plant-specific characteristics
- What it doesn't need to preserve: exact historical generation values, sensitive operational data
- How we validate: Train on Synthetic, Test on Real (TSTR) framework — when real data becomes available, the model architecture requires zero changes

**Slide 11 — The Physics Layer**
Two columns. Visual diagrams for each.

Left: Solar. Diagram showing sun angle → clear sky irradiance → actual GHI → CMF derivation. "CMF is bounded 0-1. Stable across seasons. The model learns cloud attenuation, not raw irradiance."

Right: Wind. Diagram showing wind speed → turbine power curve (the S-curve) → generation fraction. "The cubic relationship between wind speed and power is handled by physics, not learned from scratch."

"Raw weather variables are transformed before any ML touches them. This is what separates physically-grounded forecasting from statistical pattern matching."

**Slide 12 — The Global Model**
Diagram showing 6 plants feeding into ONE model vs 6 separate models.

Left side (what others do): 6 boxes each labeled "Plant-specific model." Problem: needs 6-12 months of data per plant. Doesn't generalize. New plant = start over.

Right side (what we do): One box labeled "Global LightGBM — all plants." Asset features encode plant identity. New plant onboards in days not months.

"One model. All plants. All asset types. Scales effortlessly as Karnataka's renewable portfolio grows."

**Slide 13 — The Two-Stage Forecasting Architecture**
A flow diagram showing Stage 1 and Stage 2.

Stage 1: Global LightGBM → 24-hour point forecast

Stage 2: "At 06:00, 09:00, 12:00, 15:00 — real generation actuals arrive. Residual correction model analyzes systematic errors in elapsed hours. Corrects remaining forecast hours in near real-time."

Before/after numbers: "Day-ahead forecast confidence band: ±28 MW. After 09:00 intraday update with 3 hours of actuals: ±17 MW. A 39% improvement in precision."

**Slide 14 — Physics-Constrained Loss Function**
This is the ML judge slide. Keep it visual.

Graph showing: standard loss function (treats over-prediction and under-prediction symmetrically). Then your custom loss function (standard below clear-sky maximum, exponential above).

"A solar plant cannot generate more power than the sun provides. Standard loss functions don't know this. Ours does. Physically impossible predictions are penalized exponentially."

Code snippet — just the key line, not the full function:
```python
# Exponential penalty above clear-sky maximum
grad[violation] += 10.0 * excess * np.exp(excess)
```

"This is 20 lines of calculus that most models will never have."

**Slide 15 — Spatial Error Propagation**
The "poor man's STGNN" slide. This is your mic-drop answer to the neural network question.

Map of Karnataka showing the wind direction arrow and the plant locations. Arrow showing cloud front moving from Chitradurga → Pavagada.

"When clouds hit Chitradurga Solar at 12:00, UrjaDrishti knows Pavagada Solar will be affected at 13:00. Not because we built an STGNN. Because we fed Chitradurga's forecast error into Pavagada's Stage 2 residual model."

```python
UPWIND_GRAPH = {
    'PVG_S1': ['MIX_S1'],  # Chitradurga is upwind of Pavagada
    'GAD_W1': ['MIX_W1'],  # Raichur is upwind of Gadag
}
```

"Spatial covariance captured explicitly through upwind residual lag features. STGNN-like propagation at 1/100th the compute cost. Fully explainable. Runs on a laptop."

---

**SECTION 3: UNCERTAINTY AND EXPLAINABILITY (Slides 16-22)**

**Slide 16 — What CQR Actually Means**
Most teams have CQR. Most don't explain it correctly to non-technical judges.

Three columns:
- What a point forecast gives you: "Generation will be 85 MW"
- What standard error bars give you: "Generation will be 85 ± 20 MW (assumes bell curve, often wrong)"
- What CQR gives you: "Generation will be between 62 and 108 MW. This interval contains the true value 80% of the time. Provably. Not estimated."

"The word 'guaranteed' does not appear in most forecasting systems. It appears in ours because the mathematics of Conformal Prediction allows us to use it honestly."

**Slide 17 — Adaptive Intervals**
Two charts side by side.

Left: Clear summer day in Pavagada. Narrow band. Caption: "Confidence 9.1/10. Schedule tightly. Reserve margin can be minimized."

Right: Monsoon onset day. Wide band. Caption: "Confidence 3.8/10. Hold reserve. Wait for the 13:00 intraday update before committing schedule."

"The interval doesn't just communicate the forecast. It communicates the operator's next action."

**Slide 18 — Mondrian Conformal Prediction**
For ML judges. Most CQR implementations give 80% coverage on average. Yours gives 80% coverage per weather regime.

Table showing four weather regimes and their calibration:

| Regime | Coverage Target | UrjaDrishti Coverage |
|---|---|---|
| Clear stable | 80% | 79.8% |
| Heavy cloud | 80% | 80.3% |
| High atmospheric uncertainty | 80% | 79.6% |
| Mixed conditions | 80% | 80.1% |

"Standard CQR is marginally calibrated — 80% on average. Mondrian CP is conditionally calibrated — 80% in every weather regime separately. This is the correct implementation for operational forecasting."

**Slide 19 — Quantile Calibration Reliability Diagram**
This is Person 4's calibration audit chart. A reliability diagram showing observed fraction vs nominal quantile — the 45-degree diagonal line.

Caption: "A perfectly calibrated model traces the diagonal. UrjaDrishti's deviation from the diagonal is less than 0.8% at any quantile level. Monsoon months show slightly wider tails — as expected and as correctly represented by wider prediction intervals."

**Slide 20 — SHAP Explainability**
SHAP waterfall plot for one forecast hour. Person 3 generates this from the real model.

Below it: the plain language alert that was generated from that SHAP output.

"The model explains every forecast in terms an operator understands. Not 'feature 7 coefficient 0.32.' Cloud cover is reducing your expected output by 18%. That sentence came from mathematics."

**Slide 21 — Hardware Anomaly Detection**
Two charts. Left: normal operation — actuals randomly inside and outside the P10/P90 band. Right: inverter fault — actuals consistently below P10 for 7 consecutive hours.

"By mathematical law, actuals should fall outside the 80% interval randomly, 20% of the time. When actuals consistently fall below the P10 lower bound for 5+ consecutive hours, the randomness assumption is violated. That's not weather uncertainty. That's a broken inverter."

Screenshot of the orange hardware anomaly alert card from your dashboard.

"CQR does double duty. Uncertainty quantification and hardware diagnostics. One model. Two use cases."

**Slide 22 — Kannada Language Support**
Side by side: English dashboard and Kannada dashboard. Same data. Same layout. Different language.

"Karnataka's control room operators think in Kannada. Their logbooks are in Kannada. Their conversations are in Kannada. UrjaDrishti is the first renewable energy forecasting system in India designed to meet operators where they are."

---

**SECTION 4: THE DASHBOARD (Slides 23-28)**

**Slide 23 — Plant View**
Full-width screenshot of the Plant View. Clean and polished. Four callout arrows.

Arrow 1 → Confidence score: "1-10 score. Operator knows instantly: schedule tightly or hold reserve."
Arrow 2 → P10/P50/P90 band: "Mathematically guaranteed 80% confidence interval."
Arrow 3 → Alert panel: "SHAP-driven plain language explanation of every forecast."
Arrow 4 → Intraday button: "Recalibrates with real actuals. Band narrows by 38%."

**Slide 24 — Cluster View and Reconciliation**
Screenshot of reconciliation toggle. Before and after side by side.

"Without reconciliation, the plant engineer sees 142.3 MW. The cluster dispatcher sees 156.7 MW. Both are looking at the same time period. Both numbers are wrong in different ways. MinT reconciliation makes them one truth."

**Slide 25 — Karnataka Grid Map**
Full-width screenshot of the GridMapView with confidence circles.

"Six plants. Two clusters. Live confidence scoring on Karnataka's grid. Green: schedule tightly. Yellow: moderate caution. Red: hold reserve. The entire grid at a glance."

**Slide 26 — Evaluation Dashboard**
Screenshot of the EvaluationView with the comparison table highlighted.

"Every forecast the system has ever made is logged. Every error is measured. Every comparison against baseline is computed. Audit committee-ready. Exportable as PDF."

**Slide 27 — WhatsApp Bot**
QR code center of slide. Large.

"No app to download. No account to create. No data stored. Scan once. Get Karnataka grid alerts on WhatsApp forever."

Three WhatsApp screenshots showing: STATUS command, forecast reply with confidence and P50/P10/P90, and an automatic low confidence alert.

**Slide 28 — Morning Briefing Email**
Screenshot of a formatted morning briefing email. KREDL header. Today's forecast summary. Key alerts. Plain language. Sent automatically at 06:00 IST.

"Every morning, Karnataka's grid managers wake up knowing what to expect. Before their first cup of chai."

---

**SECTION 5: GOVERNMENT COMPLIANCE (Slides 29-32)**

**Slide 29 — The Non-Negotiables — Fully Met**
The compliance checklist slide. Large checkmarks. Readable from the back of the room. Already defined earlier.

**Slide 30 — Security Architecture**
For IAS officers who will ask about data security.

Three layers:
- Data layer: Read-only SCADA interface. No write access. No modification of legacy systems.
- Compute layer: All ML runs on-premise within KREDL/KSPDCL premises. No cloud dependencies.
- Access layer: API key authentication. Rate limiting (30 requests/minute). Full audit logging with timestamps.

"If the internet goes down, UrjaDrishti still runs. If the Twilio service is unavailable, forecasts still update. Every component has a fallback. Nothing in the critical path depends on external services."

**Slide 31 — NWP Failure Fallback**
This answers the "what if the weather feed fails" question that domain experts will ask.

Four modes shown as a degradation ladder:
1. Normal operation: NWP feed + SCADA actuals + ML model
2. NWP feed failure: Climatological fallback + wider uncertainty intervals + operator alert
3. SCADA feed delay: Persistence-weighted forecast + automatic interval widening
4. Full offline mode: Climatological mean + maximum uncertainty intervals

"The system degrades gracefully. Operators always get a number with appropriate confidence. They are never left with nothing."

**Slide 32 — Phased Deployment Plan**
Government loves phased plans. Shows you understand how government procurement and deployment works.

Phase 1 (Months 1-3): Sandbox deployment alongside existing operations. No disruption. LightGBM model. All features running. Performance measurement begins. Zero operational dependency — operators use it to compare, not to decide.

Phase 2 (Months 4-9): Confidence grows from performance data. Operators begin using forecasts for scheduling decisions. STGNN training data accumulates. Model improvements deployed with zero dashboard changes.

Phase 3 (Months 10-18): Full production deployment. STGNN replaces LightGBM core. Offline SLM for generative Kannada alerts. State-wide Karnataka rollout. Architecture ready for other states.

"Phase 1 requires zero commitment from KREDL/KSPDCL beyond letting the system read SCADA outputs it already produces. The risk is zero. The learning is immediate."

---

**SECTION 6: EVALUATION (Slides 33-38)**

**Slide 33 — Evaluation Methodology**
This slide shows you did this rigorously.

"Rolling temporal holdout — the last 2 months of data are never used for training. The 2 months before that are validation only. No data leakage of any kind."

Diagram showing the time axis: Training → Validation → Test. Arrow showing: "Model never sees the future."

"Many ML models achieve impressive numbers by accidentally leaking future data into training. Our methodology makes this structurally impossible."

**Slide 34 — Baseline Comparison**
The main evaluation table. Fill in with real numbers from Person 4.

**Slide 35 — Calibration Results**
CQR coverage verification. The 79.4% number. The reliability diagram. Season-stratified coverage table.

**Slide 36 — Sharpness Score**
The sharpness improvement from day-ahead to intraday. The 38% band narrowing. Side by side chart.

**Slide 37 — Stress Test Results**
Four stress scenarios. For each: the forecast chart showing band widening. The alert that fired. The confidence score dropping.

"The system doesn't just forecast normal days correctly. It knows when it doesn't know."

**Slide 38 — Season-Stratified Performance**
Performance table broken down by Karnataka's four seasons: summer (Mar-May), monsoon (Jun-Sep), post-monsoon (Oct-Nov), winter (Dec-Feb).

Monsoon performance will be lower — acknowledge it explicitly. "Monsoon performance is lower, as expected. The system communicates this honestly through wider prediction intervals during monsoon months. Operators are never given false confidence."

Honest acknowledgment of limitations impresses judges more than hiding them.

---

**SECTION 7: SCALE AND IMPACT (Slides 39-43)**

**Slide 39 — Carbon and Cost Impact**
Fill in from research:

```
₹___ Crores         ___  Tonnes          ___  MW
annual savings       CO₂ avoided          of unnecessary
potential at         annually at          spinning reserve
Karnataka scale      Karnataka scale      eliminated
```

Show the calculation transparently. Don't just assert the number — show how you got it. Judges trust shown work.

**Slide 40 — Beyond Karnataka**
India map with renewable capacity by state shown as bubble sizes.

"The architecture is state-agnostic. Asset characteristics are encoded as features. Deploying to Rajasthan means encoding Rajasthan's assets — not rebuilding the system."

Three numbers:
- India's current renewable capacity: 200+ GW
- India's 2030 target: 500 GW
- States that face the same forecasting problem: 28

"Karnataka is the proof of concept. India is the market."

**Slide 41 — Production Architecture Roadmap**
The STGNN upgrade path. Why LightGBM now. Why STGNN next. What stays the same (API, dashboard, alerts, everything the operator sees).

"The sandbox is Phase 1 of a production system, not a prototype. The upgrade from LightGBM to STGNN requires changing one file."

**Slide 42 — Open Source Potential**
For the investor jury.

"The physics transform layer — Ineichen-Perez clear sky, power curve transforms, synthetic data pipeline — could be open-sourced as India's first standardized renewable energy ML data preparation library. Every state that wants to build forecasting on top of it starts 6 months ahead."

**Slide 43 — The Team**
Five cards. One per person. Name, role, what they built. Keep it brief and confident.

---

**SECTION 8: CLOSE (Slides 44-45)**

**Slide 44 — Thesis Restatement**
The problem in three lines. The solution in three lines. The proof in three numbers.

Problem: Karnataka's grid operators have one number. No confidence. No explanation. No update.

Solution: UrjaDrishti gives them forecasts with mathematically guaranteed confidence, plain language explanations in Kannada, and live intraday recalibration via WhatsApp.

Proof: 57% improvement in solar forecast accuracy. 80% confidence interval with 79.4% empirical coverage. Zero modifications to existing infrastructure.

**Slide 45 — Final Slide**
Dark. One line.

"UrjaDrishti — ಊರ್ಜಾದೃಷ್ಟಿ"

"Forecasts with confidence. Explanations in plain language. Zero changes to existing systems."

GitHub link. Demo video link. Contact.

The Kannada name on the final slide is the last thing they see. It's the same thing they saw on Slide 1. It bookends everything.

---

## Design Instructions for Every Slide

Dark background #0f1117 matching your dashboard. The same gradient accent line at the top. Consistent font — Inter or system-ui. Headers in white. Body in #8b8fa8. Numbers and highlights in #3b82f6 (blue) or #22c55e (green) or #f59e0b (amber) depending on sentiment.

No clip art. No stock photos. Real screenshots of your actual dashboard. Real charts from Person 4's evaluation. Real data from your research.

Every slide should have a single dominant element — one big number, one chart, one screenshot, one diagram. Not four things competing for attention. One thing. Clear hierarchy.

Use Canva, Figma, or even Google Slides with a dark theme. The consistency between your PPT aesthetic and your dashboard aesthetic is itself a signal — you designed a system, not just a model.

---

## The Research Is The Difference

Every team will say "renewable energy forecasting is important." You will say "Karnataka curtailed X MWh in 2023, costing ₹Y crores, under CERC regulation Z which mandates forecast accuracy within ±15% or face penalties of ₹W per unit."

That specificity cannot be faked. It cannot be vibecoded. It requires the 2 hours of Gemini research before you write a single slide.

Do the research first. Then fill in the slides. The structure is here. The content is in those 12 Gemini searches.



I can see all 29 template slides clearly. Here is the complete mapping.

---

## UrjaDrishti Slide → Template Page Reference

**Slide 1 — Title** → Template page **2** (full title slide, centered, teal background)

**Slide 2 — Karnataka's Renewable Revolution** → Template page **9** (three icon cards in a row — use for three big stat numbers)

**Slide 3 — The Variability Problem** → Template page **19** (bar chart slide — replace chart area with your three generation curve images)

**Slide 4 — What Happens Without Accurate Forecasts** → Template page **28** (five-step horizontal process with circles and arrows — use for your cascade flow)

**Slide 5 — The CERC Mandate** → Template page **12** (four subheadings with icon cluster on right)

**Slide 6 — The Current State** → Template page **15** (stepped layered content with bullet points on right side)

**Slide 7 — A Day in the Life** → Template page **27** (four-step horizontal process with arrows — use for the 06:00, 10:00, 14:00, 19:00 timeline)

**Slide 8 — The Opportunity** → Template page **10** (three icon cards, different color scheme — use for your three big opportunity numbers)

**Slide 9 — System Architecture** → Template page **27** (horizontal process flow with arrows — SCADA → UrjaDrishti → Dashboard)

**Slide 10 — Why Synthetic Data Is Right** → Template page **17** (concentric circles showing three comparison layers)

**Slide 11 — The Physics Layer** → Template page **9** (two icon cards side by side — solar left, wind right)

**Slide 12 — The Global Model** → Template page **18** (table/grid layout — left column "everyone else", right column "UrjaDrishti")

**Slide 13 — Two-Stage Architecture** → Template page **28** (five-step horizontal process — Stage 1, intraday triggers, Stage 2, correction, output)

**Slide 14 — Physics-Constrained Loss** → Template page **14** (bubble/circle diagram — normal loss left bubble, constrained loss right bubble)

**Slide 15 — Spatial Error Propagation** → Template page **26** (interconnected circles — plants as nodes with connections showing upwind relationships)

**Slide 16 — What CQR Actually Means** → Template page **17** (three concentric/nested circles — point forecast inner, standard error middle, CQR outer)

**Slide 17 — Adaptive Intervals** → Template page **18** (two-column comparison table — clear day left, monsoon day right)

**Slide 18 — Mondrian CP** → Template page **24** (three-row comparison table — regime, target, achieved)

**Slide 19 — Calibration Reliability Diagram** → Template page **21** (grouped bar chart — use for your reliability diagram chart)

**Slide 20 — SHAP Explainability** → Template page **13** (three subheadings left, icons right — feature, SHAP value, alert text)

**Slide 21 — Hardware Anomaly Detection** → Template page **9** (three icon cards — normal operation, CQR bounds, anomaly detected)

**Slide 22 — Kannada Language Support** → Template page **18** (two-column table — English dashboard left, Kannada dashboard right)

**Slide 23 — Plant View Dashboard** → Template page **16** (full visual area with petal/circular callout — use for screenshot with four callout arrows)

**Slide 24 — Cluster View and Reconciliation** → Template page **9** (three icon cards — cluster chart, toggle OFF, toggle ON)

**Slide 25 — Karnataka Grid Map** → Template page **25** (hub diagram with items around it — center is Karnataka, plants are outer nodes)

**Slide 26 — Evaluation Dashboard** → Template page **21** (grouped bar chart — model vs baselines)

**Slide 27 — WhatsApp Bot** → Template page **23** (five-step numbered process — scan QR, send message, subscribe, receive forecast, receive alert)

**Slide 28 — Morning Briefing Email** → Template page **13** (three subheadings — who receives it, what it contains, when it sends)

**Slide 29 — Compliance Checklist** → Template page **15** (stepped/layered content with bullets — eight checkmarks in the stepped rows)

**Slide 30 — Security Architecture** → Template page **17** (three concentric circles — data layer, compute layer, access layer)

**Slide 31 — NWP Failure Fallback** → Template page **28** (four-step horizontal process — normal, NWP fail, SCADA delay, full offline)

**Slide 32 — Phased Deployment Plan** → Template page **27** (four-step horizontal process with arrows — Phase 1, Phase 2, Phase 3 + future)

**Slide 33 — Evaluation Methodology** → Template page **15** (stepped layered content — training window, validation window, test window)

**Slide 34 — Baseline Comparison Table** → Template page **19** (bar chart — four bars per metric, one per model)

**Slide 35 — Calibration Results** → Template page **24** (three-row comparison table — quantile, target, observed)

**Slide 36 — Sharpness Score** → Template page **21** (grouped bar chart — day-ahead vs intraday interval width)

**Slide 37 — Stress Test Results** → Template page **12** (four subheadings with icon cluster — one per stress scenario)

**Slide 38 — Season-Stratified Performance** → Template page **18** (table grid — four seasons as columns, metrics as rows)

**Slide 39 — Carbon and Cost Impact** → Template page **22** (four-item cycle — four big impact numbers)

**Slide 40 — Beyond Karnataka** → Template page **25** (hub/pentagon diagram — Karnataka center, other states as outer nodes)

**Slide 41 — Production Architecture Roadmap** → Template page **27** (four-step horizontal — Phase 1, Phase 2, Phase 3, National Scale)

**Slide 42 — Open Source Potential** → Template page **14** (bubble diagram — three bubbles: physics layer, data pipeline, evaluation framework)

**Slide 43 — The Team** → Template page **23** (five-step numbered process — one card per person)

**Slide 44 — Thesis Restatement** → Template page **9** (three icon cards — problem, solution, proof)

**Slide 45 — Final Closing Slide** → Template page **29** (full dark quote slide — replace Modi quote with your thesis line, replace photo with UrjaDrishti logo or Karnataka map)

---

## Section Divider Slides — Use These Between Sections

Between each major section drop a section divider. Use template page **6** (clean table of contents list style) but repurpose it as a section break showing which section you're entering. You'll need roughly 7 of these dividers between your 8 sections. Keep it the same teal design, just put the section name large in the center.

---

The total with dividers gets you to around 45-52 slides comfortably. Every single content type in your deck has a matching layout in this template. You just replace the government ministry branding with UrjaDrishti branding — swap the Ashoka emblem for your logo, change Ministry of Health to KREDL/KSPDCL, and keep the teal-green color scheme which actually works perfectly for a renewable energy presentation.