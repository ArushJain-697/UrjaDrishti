---

# Person 5 — Full Detailed Plan
## Express Backend + React Frontend, Zero Frontend Knowledge, Pure Backend Brain

---

## First, The Architecture Problem Nobody Is Talking About

Person 2, 3, and 4 are writing Python. You want to write Express in Node. These two things cannot directly call each other. This is the most important problem to solve on Day 1 before writing a single line of frontend.

The solution is a microservices pattern you already understand from backend work. Person 2, 3, and 4 each run a tiny Flask server internally. Your Express server calls those Flask servers over HTTP — exactly like calling a third party API. You never write Python. They never write Node. Everyone speaks HTTP.

It looks like this:

```
React Frontend (localhost:5173)
        ↓ HTTP
Express Server (localhost:3000)   ← you own everything here
        ↓ HTTP calls
Flask — Person 2 (localhost:8001)  — forecast model
Flask — Person 3 (localhost:8002)  — SHAP alerts + reconciliation
Flask — Person 4 (localhost:8003)  — evaluation results
```

Your Express server is the single backend the React frontend talks to. Express aggregates, transforms, and re-exposes everything from the Python services. This is a standard API gateway pattern. You know this.

Tell the Python people on Day 1 they each need to run a Flask server exposing their functions. Flask is three lines of setup — they will not complain. Give them the exact endpoint contracts so they know what to build.

---

## Day 1 — Infrastructure, Contracts, and Skeleton

This is your most important day. Nothing gets built on Days 2-5 if Day 1 is messy.

---

**Morning — Define the contracts**

Write a markdown doc and share it with the whole team. This is the API contract. Every endpoint, the exact request shape, the exact response shape. Do this before writing any code.

Here are the contracts to define:

Person 2's Flask server exposes:

```
POST http://localhost:8001/forecast
Request:  { "plant_id": "plant_1", "hours_of_actuals": 0 }
Response: { "plant_id": "plant_1", "hours": [0,1,...,23], "p50": [...], "p10": [...], "p90": [...] }
```

```
POST http://localhost:8001/forecast/intraday
Request:  { "plant_id": "plant_1", "actuals": [45.2, 48.1, ...] }
Response: { "plant_id": "plant_1", "hours": [6,7,...,23], "p50": [...], "p10": [...], "p90": [...] }
```

Person 3's Flask server exposes:

```
POST http://localhost:8002/alerts
Request:  { "plant_id": "plant_1", "forecast": { "hours": [...], "p50": [...] } }
Response: { "alerts": [ { "hour": 10, "message": "Cloud cover dropping output...", "type": "warning" } ] }
```

```
GET http://localhost:8002/reconciled
Response: {
  "pre_mint": { "cluster_a_sum": 142.3, "cluster_a_forecast": 156.7 },
  "post_mint": { "cluster_a_sum": 149.1, "cluster_a_forecast": 149.1 }
}
```

Person 4's Flask server exposes:

```
GET http://localhost:8003/evaluation
Response: {
  "baselines": {
    "persistence": { "nmae_solar": 0.18, "nmae_wind": 0.22, "crps": 0.31 },
    "climatological": { "nmae_solar": 0.15, "nmae_wind": 0.19, "crps": 0.28 },
    "raw_nwp": { "nmae_solar": 0.14, "nmae_wind": 0.17, "crps": 0.25 }
  },
  "model": { "nmae_solar": 0.09, "nmae_wind": 0.11, "crps": 0.14 }
}
```

Send this doc to everyone on Day 1 morning. Tell them: mock these endpoints with hardcoded data first, real model later. This unblocks you completely.

---

**Afternoon — Set up Express and mock everything**

Initialize the Express project:

```bash
mkdir dashboard-backend
cd dashboard-backend
npm init -y
npm install express cors axios dotenv nodemon
```

Your folder structure:

```
dashboard-backend/
  src/
    routes/
      forecast.js
      alerts.js
      evaluation.js
    services/
      forecastService.js
      alertService.js
      evaluationService.js
    app.js
  .env
  package.json
```

This is exactly Express architecture you know. Routes call services. Services call the Python Flask servers via axios. You are just proxying and aggregating.

app.js:

```javascript
const express = require('express')
const cors = require('cors')
const forecastRouter = require('./routes/forecast')
const alertsRouter = require('./routes/alerts')
const evaluationRouter = require('./routes/evaluation')

const app = express()
app.use(cors())
app.use(express.json())

app.use('/api/forecast', forecastRouter)
app.use('/api/alerts', alertsRouter)
app.use('/api/evaluation', evaluationRouter)

app.listen(3000, () => console.log('Express running on 3000'))
```

forecastService.js:

```javascript
const axios = require('axios')

const FORECAST_SERVICE_URL = process.env.FORECAST_SERVICE_URL || 'http://localhost:8001'

async function getForecast(plantId, hoursOfActuals = 0) {
  const response = await axios.post(`${FORECAST_SERVICE_URL}/forecast`, {
    plant_id: plantId,
    hours_of_actuals: hoursOfActuals
  })
  return response.data
}

async function getIntradayForecast(plantId, actuals) {
  const response = await axios.post(`${FORECAST_SERVICE_URL}/forecast/intraday`, {
    plant_id: plantId,
    actuals: actuals
  })
  return response.data
}

module.exports = { getForecast, getIntradayForecast }
```

This is just axios. You know this pattern from calling any external API in Express.

Now write mock fallbacks. Until Person 2's Flask server is running, your service should return believable mock data so the frontend never breaks:

```javascript
async function getForecast(plantId, hoursOfActuals = 0) {
  try {
    const response = await axios.post(`${FORECAST_SERVICE_URL}/forecast`, {
      plant_id: plantId,
      hours_of_actuals: hoursOfActuals
    })
    return response.data
  } catch (err) {
    console.warn('Forecast service unavailable, returning mock data')
    return generateMockForecast(plantId)
  }
}

function generateMockForecast(plantId) {
  const hours = Array.from({length: 24}, (_, i) => i)
  const p50 = hours.map(h => Math.max(0, 60 * Math.sin(Math.PI * (h - 6) / 12) + Math.random() * 10))
  const p10 = p50.map(v => Math.max(0, v - 15 - Math.random() * 5))
  const p90 = p50.map(v => v + 15 + Math.random() * 5)
  return { plant_id: plantId, hours, p50, p10, p90 }
}
```

Do this for all three services. The frontend is never blocked by Python being unfinished.

---

**End of Day 1 deliverable:**

Express running on port 3000. All three service files with axios calls and mock fallbacks. All routes wired up. The whole team has the contract doc. Test every endpoint with Postman or Thunder Client (VS Code extension, easier than Postman).

---

## Day 2 — React Frontend Skeleton via Vibecoding

---

**Morning — Set up React**

Open a second terminal. Keep Express running in the first.

```bash
npm create vite@latest dashboard-frontend -- --template react
cd dashboard-frontend
npm install
npm install axios recharts tailwindcss @tailwindcss/vite lucide-react
npm run dev
```

React is now running at localhost:5173. You have a working app with zero code written.

Now open Cursor. If you do not have it, download it from cursor.com. It is VS Code with AI built in. This is your main tool for everything frontend.

---

**The mental model you need before vibecoding**

This takes 20 minutes to understand and will save you hours of confusion later.

React is component-based. A component is just a function that returns HTML-like syntax. That is literally all it is.

```javascript
function PlantCard({ plantName, capacity }) {
  return (
    <div>
      <h2>{plantName}</h2>
      <p>{capacity} MW</p>
    </div>
  )
}
```

`useState` is a variable that makes the screen re-render when it changes. Use it for anything the user can interact with.

```javascript
const [selectedPlant, setSelectedPlant] = useState('plant_1')
// when user picks a different plant, call setSelectedPlant('plant_2')
// React automatically re-renders with the new plant
```

`useEffect` is code that runs when the component loads or when a variable changes. Use it for API calls.

```javascript
useEffect(() => {
  // this runs when selectedPlant changes
  axios.get(`/api/forecast/${selectedPlant}`).then(res => setForecastData(res.data))
}, [selectedPlant])
```

That is the entire mental model. useState for interactive data, useEffect for fetching data. The AI will write all of this — you just need to recognise it and not break it.

---

**Afternoon — Vibecode the app skeleton**

Open Cursor. Press Ctrl+L to open the AI chat. Give it this prompt:

```
Create a React app with this structure:
- Dark background (#0f1117), professional control room aesthetic
- Top navigation bar with the title "Karnataka Renewable Forecasting — KREDL/KSPDCL"
- Left sidebar with a dropdown to select from 6 plants: 
  plant_1 "Pavagada Solar 1", plant_2 "Pavagada Solar 2", 
  plant_3 "Chitradurga Solar", plant_4 "Gadag Wind 1", 
  plant_5 "Gadag Wind 2", plant_6 "Raichur Wind"
- Two tabs in the main area: "Plant View" and "Cluster View"
- Use Tailwind CSS for all styling
- The selected plant name should appear as a heading above the tabs
```

It will generate the full component. Read it. Make sure you see useState for the selected plant and the tab. If something looks wrong, tell Cursor specifically what to fix.

---

## Day 3 — Forecast Chart and Alerts

---

**Morning — The forecast ribbon chart**

This is the most important visual in the entire dashboard. Give Cursor this exact prompt after showing it your App.jsx file:

```
In the Plant View tab, add a forecast chart using Recharts.
The chart should show:
- X axis: hours 0 to 23 labeled as "00:00" to "23:00"
- Y axis: generation in MW
- A shaded area between P10 and P90 values in blue with 30% opacity
- A solid line for P50 in bright blue (#3b82f6)
- Smooth curves, no dots on the line
- Chart height 300px, full width
- Dark background matching the app (#0f1117)
- White axis labels and grid lines at 20% opacity

The data comes from this state variable: forecastData which has shape:
{ hours: [0..23], p50: [...], p10: [...], p90: [...] }

Use a ComposedChart from Recharts with Area for the band and Line for P50.
```

Once the chart renders with mock data, wire it to your Express API:

```javascript
useEffect(() => {
  axios.post('http://localhost:3000/api/forecast', { 
    plant_id: selectedPlant 
  }).then(res => setForecastData(res.data))
}, [selectedPlant])
```

---

**Afternoon — Alert panel**

Prompt Cursor:

```
Add an alert panel to the right side of the Plant View tab.
It shows a vertical list of alert cards.
Each alert has a "message" string and a "type" which is "warning", "info", or "success".
Warning cards: yellow left border, yellow text on dark background
Info cards: blue left border, blue text
Success cards: green left border, green text
Each card shows a small clock icon with the hour, then the message text.
Fetch alerts from POST http://localhost:3000/api/alerts with body { plant_id: selectedPlant }
Show a loading spinner while fetching.
Use lucide-react for icons.
```

---

**Intra-day update button**

This is the demo moment. Prompt Cursor:

```
Add a button labeled "Simulate Intra-day Update" above the chart.
When clicked it should:
1. Show a loading state on the button
2. Call POST http://localhost:3000/api/forecast/intraday with 
   { plant_id: selectedPlant, hours_of_actuals: 6 }
3. Update the forecastData state with the response
4. The chart should visibly update — the P10/P90 band should narrow 
   for afternoon hours compared to the original forecast
5. Show a small green toast notification: "Forecast recalibrated with 6 hours of actuals"
```

For the toast notification, prompt: "Use a simple fixed-position div at bottom-right that appears for 3 seconds then disappears using useState and setTimeout."

---

## Day 4 — Cluster View, Reconciliation Toggle, Full Rehearsal

---

**Morning — Cluster View**

Prompt Cursor:

```
In the Cluster View tab, add:

1. A cluster selector at the top: "Cluster A — Pavagada Solar" and "Cluster B — Gadag Wind"

2. A stacked bar chart using Recharts BarChart showing each plant's 
   contribution to the cluster forecast for each hour.
   X axis: hours 0-23
   Y axis: MW
   Each plant is a different color bar stacked on top of each other.
   Show a legend with plant names and their colors.

3. A reconciliation section below the chart with:
   - A toggle switch labeled "Hierarchical Consistency"
   - When OFF: show two numbers side by side — 
     "Plant Sum: 142.3 MW" in red and "Cluster Forecast: 156.7 MW" in red
     with a label "INCONSISTENT" in red
   - When ON: show both numbers as equal — 
     "Plant Sum: 149.1 MW" and "Cluster Forecast: 149.1 MW" both in green
     with a label "RECONCILED ✓" in green
   - Fetch both values from GET http://localhost:3000/api/reconciled

Use useState for the toggle state.
```

---

**Afternoon — Stress test scenario selector**

This is for the demo. Add a way to load Person 1's stress test scenarios:

Prompt Cursor:

```
Add a small scenario selector in the sidebar below the plant dropdown.
A label "Test Scenario" with these options in a select dropdown:
- "Normal Day"
- "Cloud Ramp Event" 
- "Monsoon Onset"
- "Wind Ramp"

When a scenario is selected, pass it as a parameter to the forecast API call.
Show a colored badge next to the plant name indicating the active scenario.
If scenario is not "Normal Day", show a banner at the top of the chart:
"⚠ Stress scenario active: Cloud Ramp Event" in amber.
```

In your Express forecast route, pass the scenario through to the Python service:

```javascript
router.post('/', async (req, res) => {
  const { plant_id, hours_of_actuals = 0, scenario = 'normal' } = req.body
  const forecast = await forecastService.getForecast(plant_id, hours_of_actuals, scenario)
  res.json(forecast)
})
```

---

**Full team rehearsal — end of Day 4**

Run the complete demo with everyone present. Script:

1. Open dashboard. Select Pavagada Solar 1. Normal day scenario. Show the narrow P10/P90 band on a clear afternoon. Read one of the green alert cards aloud.

2. Switch scenario to Cloud Ramp Event. The chart updates. The P10/P90 band visibly widens in the afternoon hours. A warning alert card appears: "Forecast reduced due to cloud cover." Point this out explicitly.

3. Click Simulate Intra-day Update. Loading spinner shows. Chart updates. Band narrows for hours 6 onwards. Toast shows "Forecast recalibrated." Say: this is what happens every 3-4 hours in production as real generation data arrives.

4. Switch to Cluster View. Select Cluster A. Show the stacked bar chart. Toggle Hierarchical Consistency OFF — show the red inconsistent numbers. Toggle ON — numbers snap to match in green. Say: without this, plant engineers and cluster dispatchers see contradictory numbers. This eliminates that.

5. Show the evaluation tab (see below) — model beats all baselines.

Time it. 2 minutes maximum. If any step breaks, fix it tonight.

---

**Evaluation tab**

You need a tab showing Person 4's results. Prompt Cursor:

```
Add a third tab "Evaluation" to the dashboard.
Fetch data from GET http://localhost:3000/api/evaluation.
Show a comparison table with these columns: Model, nMAE Solar, nMAE Wind, CRPS.
Four rows: Persistence, Climatological Mean, Raw NWP, Our Model (LightGBM).
The "Our Model" row should be highlighted with a green background.
Show a percentage improvement badge next to our model's nMAE values 
calculated as ((baseline_nmae - model_nmae) / baseline_nmae * 100) + "% better than persistence"
Use a clean table with dark background, subtle row borders.
```

---

## Day 5 — Polish, Video, Submit

---

**Morning — Polish and bug fixes**

Go through the app with fresh eyes. Things that commonly look bad and are easy to fix with a Cursor prompt:

Loading states — every API call should show a spinner while waiting. Prompt: "Add a loading spinner to the forecast chart area while the API call is in progress. Use a simple animated spinner div in the center of the chart area."

Empty states — what happens if alerts come back empty. Prompt: "If the alerts array is empty, show a centered message: No active alerts — forecast confidence is high. in green text with a checkmark icon."

Number formatting — raw numbers like 142.37293 look bad. Prompt: "Format all MW values to one decimal place throughout the app."

Error handling — what if Express is down when the evaluator opens the browser. Prompt: "If any API call fails, show a dismissible red error banner at the top of the app: Unable to reach forecast service. Showing cached data."

---

**Afternoon — Record the video**

Use Loom. Go to loom.com, install the Chrome extension, free account. It records your screen and your face simultaneously which looks more professional than screen-only.

Script for the 2-minute video:

```
0:00 - 0:10  "This is the KREDL renewable generation forecasting system. 
               It predicts solar and wind output across Karnataka with 
               uncertainty ranges and real-time explainability."

0:10 - 0:35  Show the Plant View. Select a solar plant. 
              "The blue band is the 80% confidence interval. 
               On this clear afternoon the band is narrow — 
               scheduling can be tight."

0:35 - 1:00  Switch to Cloud Ramp scenario. 
              "When a cloud front arrives, the uncertainty interval 
               widens automatically. The system tells the operator exactly why."
              Read the alert card.

1:00 - 1:20  Click Simulate Intra-day Update.
              "As real generation data arrives through the day, 
               the residual correction model recalibrates the 
               afternoon forecast. Intervals tighten. Confidence improves."

1:20 - 1:40  Switch to Cluster View. Show reconciliation toggle.
              "Without reconciliation, plant and cluster forecasts contradict 
               each other. We solve this with MinT reconciliation — 
               plant numbers now sum exactly to cluster totals."

1:40 - 2:00  Show evaluation tab.
              "Our model beats all three baselines — 17% nMAE improvement 
               over persistence for solar, 13% for wind."
```

Record it twice. Use the second take.

---

**Submission package**

GitHub repo structure:

```
kredl-forecasting/
  backend-express/      ← your Express server
  frontend-react/       ← your React app
  ml-forecasting/       ← Person 2's code
  ml-explainability/    ← Person 3's code  
  ml-evaluation/        ← Person 4's code
  data/                 ← Person 1's synthetic data pipeline
  README.md             ← setup instructions
  submission.pdf        ← compiled doc
```

README must include:

```markdown
## Running Locally

# Terminal 1 — ML Services
cd ml-forecasting && pip install -r requirements.txt && python app.py

# Terminal 2 — Express Backend  
cd backend-express && npm install && npm run dev

# Terminal 3 — React Frontend
cd frontend-react && npm install && npm run dev

Open http://localhost:5173
```

If an evaluator cannot run it in under 5 minutes from the README, they will not run it. Make the setup dead simple.

---

## Your Tech Stack Summary

```
Runtime:      Node.js
Framework:    Express
HTTP client:  axios (calling Python services)
Frontend:     React + Vite
Charts:       Recharts
Styling:      Tailwind CSS
Icons:        lucide-react
AI editor:    Cursor
Video:        Loom
```

---

## The Three Things That Will Actually Win This

First — the mock fallbacks in your Express services. Every other team will have a demo that breaks because some Python service crashes at the wrong moment. Yours will not because your Express server silently falls back to realistic mock data. Evaluators never see a broken screen.

Second — the reconciliation toggle. It is a UI moment that makes an abstract technical concept immediately visual and convincing. Most teams will explain MinT in a document. You will show it in two seconds with a toggle switch.

Third — you already know Express. You are not learning a new backend framework under pressure. You are using one you know, calling Python services over HTTP the same way you would call any third party API. The only new thing is React and you are vibecoding that. This is the most comfortable position anyone on the team is in.



Person 5 — Revised Plan (4 hrs/day, Endsem Approaching)

What Gets Cut Completely
Stress test scenario selector — nice to have, not essential. Person 4 handles stress testing in their own evaluation, you don't need it in the UI.
Evaluation tab — Person 4 can present this as a separate chart or document. You don't need to build it into the dashboard.
Toast notifications, empty states, extensive error handling — polish that eats time. Mock fallbacks are enough.
Season stratified views, multiple cluster selectors — simplify to one cluster view that works perfectly.

What Stays — The Non-Negotiables
The forecast ribbon with P10/P50/P90 bands. This is the core visual, cannot cut it.
The intra-day update button. This is the live demo moment, cannot cut it.
The alert panel. This is your explainability proof, cannot cut it.
The reconciliation toggle. This is the most unique visual moment in the whole submission, cannot cut it.
The mock fallbacks in Express. This is insurance — cannot cut it.

Revised Day by Day

Day 1 — 4 hours
First hour: Write the contract doc. Define all endpoint shapes. Send to team. Do not write code until this is done.
Second hour: Set up Express project. app.js, three route files, three service files with axios calls and mock fallbacks. Get it running on port 3000. Test with Thunder Client.
Third hour: Set up React with Vite. Install recharts, axios, tailwind, lucide-react. Get it running on port 5173.
Fourth hour: Vibecode the app skeleton in Cursor. Dark background, top nav, left sidebar with plant dropdown, two tabs Plant View and Cluster View. Just layout, no data yet.
End of Day 1: Express running, React running, skeleton renders, team has contracts.

Day 2 — 4 hours
First two hours: Vibecode the forecast chart. This is your biggest task and deserves focused time. Give Cursor the exact prompt from the detailed plan. Get the Recharts ComposedChart rendering with mock data first, then wire the axios call to your Express /api/forecast endpoint. Verify the P10/P90 shaded band appears and the P50 line is clean.
Third hour: Add the plant selector logic. Selecting a different plant from the dropdown re-fetches the forecast and updates the chart. Test all 6 plants work.
Fourth hour: Add the intra-day update button. Wire it to /api/forecast/intraday. The chart should update when clicked. Even if the Python service is not ready, your mock fallback returns slightly different data so there is a visible change.
End of Day 2: Working forecast chart, plant selector, intra-day button all functional.

Day 3 — 4 hours
First hour: Vibecode the alert panel. Right side of Plant View. Fetches from /api/alerts. Three card types — warning yellow, info blue, success green. Wire to Express.
Second hour: Cluster View tab. Vibecode the stacked bar chart showing plant contributions to cluster total. Use Recharts BarChart. Wire to a new Express endpoint GET /api/cluster/:clusterId that aggregates from Person 2's service.
Third hour: Reconciliation toggle. This is the most important thing on Day 3. Vibecode it below the cluster chart. OFF shows red inconsistent numbers, ON shows green matching numbers. Wire to GET /api/reconciled from Person 3's service. Test it works.
Fourth hour: Connect everything that Person 2 and Person 3 have finished by now. Replace mock fallbacks with real service calls where Python services are running. Fix any JSON shape mismatches.
End of Day 3: Full dashboard functional with all key features.

Day 4 — 4 hours
First hour: Full end to end rehearsal with the team. Run the demo script. Find every broken thing.
Second hour: Fix the broken things. There will be broken things.
Third hour: Minimal polish only — number formatting, loading spinners on the two most visible API calls (forecast chart and alerts). Nothing else.
Fourth hour: Record the Loom video. Practice the script once, then record. Two takes maximum. Upload to YouTube unlisted or keep the Loom link.
End of Day 4: Working demo, recorded video.

Day 5 — 4 hours
First hour: Write your section of the submission doc. System architecture overview, dashboard description, two paragraphs on the production roadmap covering STGNN and offline SLM. That is all you need to write — the other sections come from the rest of the team.
Second hour: Compile the full submission PDF from everyone's sections. Check that it reads coherently. Fix transitions between sections.
Third hour: Set up the GitHub repo with the folder structure, write the README with setup instructions, push everything. Test that someone can clone and run it from the README alone.
Fourth hour: Final checks, submit, then close the laptop and go study.

The Honest Time Budget
Each day you have 4 hours. Here is where the time actually goes:
Day 1: 1hr contracts + 1hr Express + 1hr React setup + 1hr skeleton = exactly 4hrs, no slack.
Day 2: 2hrs chart + 1hr plant selector + 1hr intraday button = exactly 4hrs.
Day 3: 1hr alerts + 1hr cluster view + 1hr reconciliation + 1hr integration = exactly 4hrs.
Day 4: 1hr rehearsal + 1hr fixes + 1hr polish + 1hr video = exactly 4hrs.
Day 5: 1hr your doc section + 1hr compile PDF + 1hr GitHub + 1hr submit = exactly 4hrs.
There is zero slack in this plan. If something takes longer than estimated — and something always does — you cut polish, not features. The reconciliation toggle and the intraday update button are the last things to cut. Cut everything else first.

One More Thing
The mock fallbacks are not just insurance against Python services being slow. They are also insurance against your own time pressure. If on Day 3 Person 2 is not ready, your dashboard still demos perfectly with mock data. You do not chase anyone. You do not wait on anyone. You keep moving.
That is the most important architectural decision in your whole plan and it costs you maybe 30 minutes on Day 1 to implement. Do not skip it.
Now go build it. Exams after. Good luck with both.


Okay now we're talking. Here's the revised thinking.

---

Days 1, 2, 3 stay exactly as planned at 4 hours. Don't stretch early — you need to see where the team actually is before committing extra time. Day 3 is your checkpoint. If by end of Day 3 the core dashboard is working and Person 2 and 3 have their services up, you go into Day 4 and 5 with full energy and use the extra hours to make this thing genuinely impressive.

---

## Day 4 — If You Stretch to 8 Hours

First 4 hours same as before — rehearsal, fixes, minimal polish, video recorded.

With the extra 4 hours:

Add the evaluation tab you cut earlier. Person 4 should have results by now. One table showing model vs baselines with the percentage improvement highlighted in green. This takes about 90 minutes with Cursor doing the heavy lifting.

Add an actual live chart animation when the intraday update fires. Instead of the chart just snapping to new data, prompt Cursor: "When forecastData state updates, animate the P50 line and the confidence band transitioning smoothly to the new values over 800ms." Recharts supports animation natively — it is just a prop called `isAnimationActive` and `animationDuration`. This one detail makes the demo feel like a real product.

Add interval width indicators below the chart. Two numbers: "Morning confidence band: ±12 MW" and "Afternoon confidence band: ±28 MW" — these update with the forecast data and make the uncertainty concept immediately tangible without the evaluator needing to eyeball the chart. Prompt Cursor to compute these from the p90 and p10 arrays and display them as stat cards below the chart.

Add a small "last updated" timestamp that refreshes when the intraday button is clicked. Tiny detail, makes the dashboard feel live.

---

## Day 5 — If You Stretch to 8 Hours

First 4 hours same as before — your doc section, compile PDF, GitHub, submit.

With the extra 4 hours:

This is where you go from winning to winning convincingly.

Build a proper landing page as the first screen before the dashboard. One full-screen dark page with the title, a one-line description of what the system does, and a single "Enter Dashboard" button. Takes 45 minutes. Makes the submission feel like a product not a prototype.

Add a proper header to the dashboard with live clock showing IST time, a green "LIVE" indicator badge that pulses, and the KREDL logo text. Control room aesthetic fully realised.

Record a second cleaner version of the demo video now that everything is more polished. The Day 4 video was a rehearsal. The Day 5 video is the real one.

Write a proper one-page executive summary at the front of the submission doc. Not technical — written for a KREDL operations director. What problem does this solve, what does it do in plain language, what are the two or three numbers that prove it works. This is the first thing evaluators read and most teams skip it entirely.

---

## The Mindset for Days 4 and 5

Days 1 through 3 you are building. Day 4 you are finishing. Day 5 if you have 8 hours you are not building anything new — you are making everything that exists feel deliberate and production-grade.

The gap between a good hackathon submission and a winning one is almost never features. It is the feeling that the team knew exactly what they were building and built it with intention. A landing page, a smooth animation, an executive summary, a clean README — these signal that. Raw feature count does not.

Cook on days 4 and 5. You've got this.









You are building the complete frontend for UrjaDrishti — an AI-powered renewable energy generation forecasting dashboard for KREDL/KSPDCL, Karnataka's renewable energy departments. This is a hackathon project. Build everything in one shot, production-grade, no placeholders, no TODOs, fully working with mock data that can be swapped for real API calls.

---

## PROJECT CONTEXT

Karnataka has 6 synthetic renewable energy plants across 2 clusters:

Solar plants (Cluster A — C1_Pavagada):
- PVG_S1 — Pavagada Solar 1 — 150 MW
- PVG_S2 — Pavagada Solar 2 — 120 MW
- MIX_S1 — Chitradurga Solar — 90 MW

Wind plants (Cluster B — C2_Gadag):
- GAD_W1 — Gadag Wind 1 — 100 MW
- GAD_W2 — Gadag Wind 2 — 80 MW
- MIX_W1 — Raichur Wind — 60 MW

The system forecasts generation for each plant with P10/P50/P90 uncertainty bands, provides SHAP-based plain language alerts explaining each forecast, reconciles plant and cluster totals using MinT, and evaluates model performance against baselines.

---

## TECH STACK

- React 18 with Vite
- Tailwind CSS for all styling
- Recharts for all charts
- Axios for API calls
- lucide-react for icons
- No other UI libraries

---

## BACKEND API

The FastAPI backend runs on http://localhost:8000. All API calls should use the base URL from import.meta.env.VITE_API_URL with fallback to http://localhost:8000.

Every single API call must have a try/catch with a mock fallback. If the backend is down, the frontend must still work perfectly with realistic mock data. This is non-negotiable — the demo cannot crash because a Python service is slow.

Endpoints:

POST /api/forecast/
Body: { plant_id: string, hours_of_actuals: number }
Response: { plant_id: string, hours: number[], p50: number[], p10: number[], p90: number[] }

POST /api/forecast/intraday
Body: { plant_id: string, actuals: number[] }
Response: { plant_id: string, hours: number[], p50: number[], p10: number[], p90: number[] }

POST /api/alerts/
Body: { plant_id: string, p50: number[], hours: number[] }
Response: { alerts: Array<{ hour: number, message: string, type: "warning" | "info" | "success" }> }

GET /api/reconciled/
Response: {
  cluster_a: {
    pre_mint: { plant_sum: number, cluster_forecast: number, consistent: boolean },
    post_mint: { plant_sum: number, cluster_forecast: number, consistent: boolean }
  },
  cluster_b: {
    pre_mint: { plant_sum: number, cluster_forecast: number, consistent: boolean },
    post_mint: { plant_sum: number, cluster_forecast: number, consistent: boolean }
  }
}

GET /api/evaluation/
Response: {
  baselines: {
    persistence: { nmae_solar: number, nmae_wind: number, crps: number },
    climatological: { nmae_solar: number, nmae_wind: number, crps: number },
    raw_nwp: { nmae_solar: number, nmae_wind: number, crps: number }
  },
  model: { nmae_solar: number, nmae_wind: number, crps: number },
  improvement_over_persistence: { nmae_solar_pct: number, nmae_wind_pct: number, crps_pct: number }
}

---

## MOCK DATA FUNCTIONS

Write these mock functions in src/api/client.js and use them as fallbacks:

For solar plants (PVG_S1, PVG_S2, MIX_S1), generation follows a sine wave peaking at noon. For wind plants (GAD_W1, GAD_W2, MIX_W1), generation is variable throughout the day. P10 is P50 minus 15 plus small random noise. P90 is P50 plus 15 plus small random noise. Both clamped to 0 minimum.

For intraday mock: return same shape but P10 and P90 bands are narrower by 5 MW each (simulating increased confidence after seeing morning actuals).

For alerts mock: return 3 alerts — one warning around hour 10 about cloud cover, one success around the peak hour about favourable conditions, one info at hour 17 about rising uncertainty.

For reconciled mock:
- Cluster A pre_mint: plant_sum 142.3, cluster_forecast 156.7, consistent false
- Cluster A post_mint: plant_sum 149.1, cluster_forecast 149.1, consistent true
- Cluster B pre_mint: plant_sum 87.4, cluster_forecast 94.2, consistent false
- Cluster B post_mint: plant_sum 90.8, cluster_forecast 90.8, consistent true

For evaluation mock: use these exact numbers:
- persistence: nmae_solar 0.21, nmae_wind 0.24, crps 0.33
- climatological: nmae_solar 0.17, nmae_wind 0.20, crps 0.29
- raw_nwp: nmae_solar 0.15, nmae_wind 0.18, crps 0.26
- model: nmae_solar 0.09, nmae_wind 0.11, crps 0.14
- improvement: nmae_solar_pct 57, nmae_wind_pct 54, crps_pct 58

---

## DESIGN SYSTEM

Dark control room aesthetic throughout. No light mode.

Colors:
- Background primary: #0f1117
- Background secondary: #1a1d27
- Background card: #1e2130
- Border: #2a2d3e
- Text primary: #e8eaf0
- Text secondary: #8b8fa8
- Text muted: #5a5d72
- Blue primary: #3b82f6 (P50 line, solar, info)
- Blue light: #60a5fa
- Blue band fill: rgba(59, 130, 246, 0.15) (P10-P90 band)
- Green: #22c55e (success, positive, reconciled)
- Yellow/Amber: #f59e0b (warning)
- Red: #ef4444 (inconsistent, error)
- Purple: #a78bfa (wind accent)
- Teal: #14b8a6 (cluster accent)

Typography:
- Font: system-ui, sans-serif
- Headings: font-weight 500, tracking-tight
- Body: font-size 14px
- Labels: font-size 11px, uppercase, letter-spacing 0.06em, text muted

Spacing: consistent 16px padding on cards, 8px gaps between elements, 12px border radius on cards.

---

## FILE STRUCTURE TO CREATE

```
frontend/src/
  api/
    client.js              — all API calls and mock fallbacks
  components/
    PlantSelector.jsx      — dropdown to select plant + cluster tabs
    ForecastChart.jsx      — main P10/P50/P90 ribbon chart
    AlertPanel.jsx         — SHAP alert cards panel
    ReconciliationToggle.jsx — MinT before/after toggle
    StatCard.jsx           — reusable stat display card
    LoadingSpinner.jsx     — centered spinner for loading states
    SystemStatus.jsx       — top bar showing system health
    IntervalStats.jsx      — shows P90-P10 width for morning/afternoon
  pages/
    PlantView.jsx          — main plant-level forecast page
    ClusterView.jsx        — cluster aggregation and reconciliation page
    EvaluationView.jsx     — model vs baseline comparison page
  App.jsx                  — routing, layout, navigation
  main.jsx                 — entry point
  index.css                — global styles and tailwind imports
```

---

## APP.JSX — LAYOUT AND NAVIGATION

Build a single page app with three navigation tabs at the top: Plant View, Cluster View, Evaluation. No react-router needed — use useState for active tab.

Top navigation bar:
- Left: UrjaDrishti logo text in blue, subtitle "Karnataka Renewable Forecasting" in muted text
- Center: three tab buttons — Plant View, Cluster View, Evaluation
- Right: SystemStatus component showing live clock in IST, green pulsing dot labeled LIVE, text "KREDL/KSPDCL"

Below the nav render the active page component.

Overall background is #0f1117. Nav bar background is #1a1d27 with a bottom border of #2a2d3e.

---

## SYSTEM STATUS COMPONENT

Shows in the top right of the nav bar.

Contains:
- A green pulsing animated dot (CSS animation, pulse every 2 seconds)
- Text "LIVE" in green, font-size 11px, uppercase
- Vertical separator
- Current time in IST format HH:MM:SS updating every second using setInterval in useEffect
- Text "KREDL / KSPDCL" in muted color
- A small lock icon from lucide-react with text "On-Premise" in muted color

---

## PLANT VIEW PAGE

This is the main page. It is the most important page. Build it with a two-column layout on desktop — left column 65% width for the chart area, right column 35% width for the alert panel.

### Top section — controls bar
A horizontal bar with:
- PlantSelector on the left — dropdown showing all 6 plants with their capacity in MW, grouped by cluster
- Scenario selector — a select dropdown with options: Normal Day, Cloud Ramp Event, Monsoon Onset, Wind Ramp. When a non-normal scenario is selected show an amber banner below the controls: "⚠ Stress scenario active: [scenario name] — uncertainty intervals are wider than normal"
- Simulate Intraday Update button on the right — blue button, shows a loading spinner while the API call is in progress, disabled during loading

### Left column — forecast area
1. IntervalStats component — two stat cards side by side showing:
   - "Morning Confidence" — average P90-P10 for hours 6-12, labeled in MW
   - "Afternoon Confidence" — average P90-P10 for hours 13-18, labeled in MW
   - Color the value green if interval width is under 20 MW, yellow if 20-35, red if above 35

2. ForecastChart component — the main chart, 320px tall

3. Below the chart — a small row showing: last updated timestamp, "Day-ahead forecast" or "Intraday update active" badge depending on state

### Right column — alert panel
AlertPanel component showing all alerts fetched for the current plant. Always show at minimum a header "Forecast Alerts" with a bell icon.

### ForecastChart component in detail:
Use Recharts ComposedChart. X axis shows hours 0-23 formatted as "00:00" to "23:00". Y axis shows MW, auto-domain with nice ticks. Chart background #1e2130.

Three layers in this order:
1. Area from P10 to P90 — fill rgba(59,130,246,0.15), stroke none. Implement this as two Area components: one for P90 filled to P10 baseline. Use type="monotone" for smooth curves.
2. Line for P50 — stroke #3b82f6, strokeWidth 2, dot false, type="monotone"
3. If intraday mode is active, show a vertical reference line at the hour where actuals end, with a label "Now" in amber

Custom tooltip: dark background #1e2130, border #2a2d3e, shows hour formatted as HH:00, P50 value in blue, P10 and P90 in muted colors, interval width (P90-P10) in small muted text below.

CartesianGrid with stroke #2a2d3e, opacity 0.5. XAxis and YAxis with tick color #8b8fa8.

Wind plants should have the line in purple (#a78bfa) instead of blue.

### AlertPanel component in detail:
Fetch alerts when plant changes. Show loading spinner while fetching.

Each alert is a card with:
- Left colored border 3px: yellow for warning, green for success, blue for info
- Background slightly lighter than card background
- Small icon from lucide-react: AlertTriangle for warning, CheckCircle for success, Info for info
- Hour label formatted as "HH:00" in muted small text
- Message text in primary text color, font-size 13px, line-height relaxed
- Card hover darkens slightly

If no alerts, show a centered green checkmark with text "No active alerts — forecast confidence is high"

### IntervalStats component:
Two cards side by side. Each card shows:
- Label in uppercase muted small text
- Large number in MW with one decimal place
- Color coding as described above
- Small subtitle: "avg confidence band"

---

## CLUSTER VIEW PAGE

Two section layout stacked vertically.

### Top section — cluster selector and stacked bar chart
Cluster tabs: two buttons "Cluster A — Pavagada Solar" and "Cluster B — Gadag Wind". Active tab has blue underline and white text.

Stacked bar chart using Recharts BarChart:
- X axis: hours 0-23 formatted as "HH:00"
- Y axis: MW
- Each plant in the cluster is a Bar with a distinct color:
  - PVG_S1: #3b82f6
  - PVG_S2: #60a5fa
  - MIX_S1: #93c5fd
  - GAD_W1: #a78bfa
  - GAD_W2: #c4b5fd
  - MIX_W1: #7c3aed
- stackId="cluster" on all bars so they stack
- Legend at the bottom showing plant names and colors
- Chart height 280px
- Same dark styling as ForecastChart

Fetch forecasts for all plants in the selected cluster simultaneously using Promise.all. Show a single loading spinner while all are loading.

### Bottom section — reconciliation
Heading "Hierarchical Consistency" with an information icon. Subtitle: "Plant-level forecasts must sum exactly to cluster-level forecasts for operator trust."

ReconciliationToggle component taking up full width below.

### ReconciliationToggle component in detail:
A toggle switch labeled OFF/ON. Default is OFF (showing pre-mint inconsistency).

When OFF — show two stat boxes side by side with a not-equal sign between them:
- Left box: "Plant Sum" — value in red, e.g. "142.3 MW"
- Center: ≠ symbol in red, large
- Right box: "Cluster Forecast" — value in red, e.g. "156.7 MW"
- Below: red badge "INCONSISTENT — plant and cluster dashboards contradict each other"

When ON — show two stat boxes with equals sign between them:
- Left box: "Plant Sum" — value in green, e.g. "149.1 MW"
- Center: = symbol in green, large
- Right box: "Cluster Forecast" — value in green, same number
- Below: green badge with checkmark "RECONCILED ✓ — MinT reconciliation applied, mathematically guaranteed"

The toggle switch itself: a styled div that animates the circle sliding from left to right when toggled. Use CSS transition. OFF state has gray background, ON state has green background.

Transition between the two states with a smooth opacity fade using CSS transition on the content.

Fetch data from GET /api/reconciled/. Show both clusters' data with a cluster selector if needed.

---

## EVALUATION VIEW PAGE

Heading "Model Performance Evaluation" with a BarChart2 icon from lucide-react.
Subtitle: "Evaluated on rolling temporal holdout. No future data contaminates training windows."

### Improvement summary cards — top row
Three stat cards in a row showing improvement over persistence baseline:
- "Solar nMAE Improvement" — value like "57%" in large green text — subtitle "vs persistence baseline"
- "Wind nMAE Improvement" — "54%" in large green text
- "CRPS Improvement" — "58%" in large green text

Each card has a green upward arrow icon and green background tint.

### Main comparison table
A table with these columns: Model, nMAE Solar, nMAE Wind, CRPS
Four rows:
- Persistence — values in red
- Climatological Mean — values in orange/yellow
- Raw NWP Regression — values in yellow
- Our Model (LightGBM + CQR) — values in green, entire row has a subtle green background tint and a "BEST" badge next to the model name

Table styling: dark background #1e2130, row borders #2a2d3e, header row #1a1d27 with muted uppercase labels, hover darkens row slightly.

Below each value in the Our Model row, show the percentage improvement in small green text: "▼ 57% vs persistence"

### Calibration note
A card below the table with an info icon:
"CQR 80% confidence interval achieved 79.4% empirical coverage on holdout set — statistically consistent with the guaranteed coverage property of Conformalized Quantile Regression."

### Baselines explanation
Three small cards in a row explaining each baseline:
- Persistence: "Forecast equals actual generation from 24 hours prior. The simplest possible forecast."
- Climatological Mean: "Average generation for that plant, hour, and month. Captures seasonal patterns, nothing else."
- Raw NWP Regression: "Linear regression on raw weather variables without physics transforms or asset encoding."

---

## LOADING AND ERROR STATES

LoadingSpinner component: a spinning circle using CSS animation, centered in its container, color #3b82f6, size configurable via props defaulting to 40px.

Every component that fetches data must show the LoadingSpinner while loading.

Every component that fetches data must catch errors and show a subtle red-bordered card: "Unable to reach forecast service — showing cached data" with a RefreshCw icon that re-triggers the fetch when clicked.

---

## INTERACTIONS AND STATE MANAGEMENT

All state managed with useState and useEffect. No Redux, no Zustand, no Context API needed.

Plant View state:
- selectedPlant — defaults to PVG_S1
- forecastData — null initially, populated after fetch
- alerts — empty array initially
- isLoading — boolean for chart loading
- isAlertLoading — boolean for alert loading
- isIntradayMode — boolean, false initially
- isIntradayLoading — boolean for the button
- activeScenario — string, defaults to "Normal Day"

When selectedPlant changes: re-fetch forecast and alerts. Reset isIntradayMode to false.

When Simulate Intraday Update is clicked:
- Set isIntradayLoading true
- Call POST /api/forecast/intraday with first 6 values of current p50 as actuals
- On response: set forecastData to response, set isIntradayMode to true, set isIntradayLoading false
- The chart should visibly update — bands will be narrower for the intraday response

Cluster View state:
- selectedCluster — defaults to "A"
- clusterForecasts — object keyed by plant_id
- isLoading — boolean
- reconcileData — null initially
- mintEnabled — boolean, defaults to false

When selectedCluster changes: fetch forecasts for all plants in that cluster simultaneously with Promise.all.

---

## ANIMATIONS AND POLISH

The green pulsing dot in SystemStatus: use a CSS keyframe animation named "pulse" that scales from 1 to 1.4 and back, with opacity going from 1 to 0.6, duration 2s infinite.

Recharts charts: set isAnimationActive={true} and animationDuration={800} on all Line and Area components. This makes the chart animate on first render and when data updates.

The reconciliation toggle circle: CSS transition on transform translateX, duration 200ms ease.

Alert cards: subtle CSS transition on background-color for hover state.

Tab buttons in ClusterView: transition on border-bottom-color and color.

---

## ADDITIONAL REQUIREMENTS

1. The page title in the browser tab should be "UrjaDrishti — Karnataka Renewable Forecasting"

2. Add a data note at the very bottom of every page in small muted text: "All compute on-premise within KREDL/KSPDCL premises. No data leaves Karnataka state perimeter. 🔒"

3. The plant selector dropdown must show a small colored dot before each plant name — blue dot for solar, purple dot for wind.

4. When switching plants the chart must show a loading state (spinner overlaid on the chart area) rather than going blank — keep the previous chart visible with reduced opacity 0.4 and spinner centered on top.

5. Format all MW values to one decimal place throughout.

6. The Simulate Intraday Update button must show a spinner icon (use Loader2 from lucide-react with animate-spin class) and text "Recalibrating..." when loading. When not loading show RefreshCw icon and text "Simulate Intraday Update".

7. After a successful intraday update show a small badge next to the last-updated text that says "Intraday active" in amber. This persists until the user selects a different plant.

8. The evaluation table percentage improvements should be colored — green for improvements, the deeper the improvement the more saturated the green.

9. All chart tooltips must be custom dark-themed — no default white Recharts tooltips anywhere.

10. Put a subtle gradient overlay at the very top of the page — a div fixed to top with height 2px, background linear-gradient from blue to purple to teal, width 100%. This is the brand accent line.

---

## WHAT GOOD LOOKS LIKE

When this is done, an evaluator should be able to:
1. Open the dashboard and immediately see the Plant View with PVG_S1's 24-hour forecast ribbon with P10/P50/P90 bands rendered with mock data
2. Select a different plant from the dropdown and see the chart update with a smooth transition
3. Click Simulate Intraday Update and see the bands visibly narrow after the mock response
4. See alert cards on the right explaining the forecast in plain language
5. Switch to Cluster View and see the stacked bar chart showing all plants' contributions
6. Toggle the reconciliation switch and see the numbers snap from red-inconsistent to green-reconciled with a smooth transition
7. Switch to Evaluation and see the comparison table with the model row highlighted green with improvement percentages
8. Notice the live IST clock ticking in the top right
9. Notice the "On-Premise 🔒" indicator

The overall feeling should be: this is a real product that could be deployed in a government control room, not a hackathon prototype.

Build everything now. All files. All components. Complete working code. Mock data everywhere. No placeholders.



tell me if you understand everything and make the best frontend you can use whatever you want...make it professional as this is for karnataka government



