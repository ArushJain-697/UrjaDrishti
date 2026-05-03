That's the energy. Let me give you everything organized so you can execute without thinking.

---

## Build Order — Exact Sequence

Do them in this order. Each one is independent so if you run out of time you have the most impactful ones done first.

---

### 1. Kannada Toggle — 3 hours, highest impression per minute

Paste this into Cursor:

---

Add a Kannada/English language toggle to the UrjaDrishti dashboard. This is a Karnataka government application and Kannada support is critical for operator usability.

Create a file `src/i18n/translations.js` with a complete translation object. English is the default, Kannada is the alternate. Here is the complete translation object to use:

```javascript
export const translations = {
  en: {
    appName: "UrjaDrishti",
    appSubtitle: "Karnataka Renewable Forecasting",
    plantView: "Plant View",
    clusterView: "Cluster View",
    evaluation: "Evaluation",
    logbook: "Logbook",
    gridMap: "Grid Map",
    live: "LIVE",
    onPremise: "On-Premise",
    simulateIntraday: "Simulate Intraday Update",
    recalibrating: "Recalibrating...",
    morningConfidence: "Morning Confidence",
    afternoonConfidence: "Afternoon Confidence",
    avgConfidenceBand: "avg confidence band",
    forecastAlerts: "Forecast Alerts",
    noAlerts: "No active alerts — forecast confidence is high",
    hierarchicalConsistency: "Hierarchical Consistency",
    hierarchicalSubtitle: "Plant-level forecasts must sum exactly to cluster-level forecasts for operator trust.",
    mintTitle: "MinT Reconciliation View",
    mintSubtitle: "Toggle OFF for pre-MinT inconsistency, ON for post-MinT reconciled totals",
    plantSum: "Plant Sum",
    clusterForecast: "Cluster Forecast",
    inconsistent: "INCONSISTENT — plant and cluster dashboards contradict each other",
    reconciled: "RECONCILED ✓ — MinT reconciliation applied, mathematically guaranteed",
    modelPerformance: "Model Performance Evaluation",
    modelSubtitle: "Evaluated on rolling temporal holdout. No future data contaminates training windows.",
    solarImprovement: "Solar nMAE Improvement",
    windImprovement: "Wind nMAE Improvement",
    crpsImprovement: "CRPS Improvement",
    vsPersistence: "vs persistence baseline",
    model: "Model",
    nmaeSolar: "nMAE Solar",
    nmaeWind: "nMAE Wind",
    best: "BEST",
    persistence: "Persistence",
    climatological: "Climatological Mean",
    rawNwp: "Raw NWP Regression",
    ourModel: "Our Model (LightGBM + CQR)",
    dayAhead: "Day-ahead forecast",
    intradayActive: "Intraday active ✓",
    lastUpdated: "Last updated",
    footerText: "All compute on-premise within KREDL/KSPDCL premises. No data leaves Karnataka state perimeter.",
    normalDay: "Normal Day",
    cloudRamp: "Cloud Ramp Event",
    monsoonOnset: "Monsoon Onset",
    windRamp: "Wind Ramp",
    clusterA: "Cluster A — Pavagada Solar",
    clusterB: "Cluster B — Gadag Wind",
    confidenceScore: "Forecast Confidence",
    safeToSchedule: "Safe to schedule tightly",
    holdReserve: "Hold reserve margin",
    highUncertainty: "High uncertainty — wait for update",
    carbonAvoided: "Carbon avoided today",
    estimatedSavings: "Est. savings today",
    liveData: "Live data",
    cachedData: "Cached data",
  },
  kn: {
    appName: "ಊರ್ಜಾದೃಷ್ಟಿ",
    appSubtitle: "ಕರ್ನಾಟಕ ನವೀಕರಿಸಬಹುದಾದ ಇಂಧನ ಮುನ್ಸೂಚನೆ",
    plantView: "ಸ್ಥಾವರ ನೋಟ",
    clusterView: "ಕ್ಲಸ್ಟರ್ ನೋಟ",
    evaluation: "ಮೌಲ್ಯಮಾಪನ",
    logbook: "ಲಾಗ್‌ಬುಕ್",
    gridMap: "ಗ್ರಿಡ್ ನಕ್ಷೆ",
    live: "ನೇರ",
    onPremise: "ಆವರಣದಲ್ಲಿ",
    simulateIntraday: "ಅಂತರ-ದಿನ ನವೀಕರಣ",
    recalibrating: "ಮರು-ಅಂಶಾಂಕನ...",
    morningConfidence: "ಬೆಳಗಿನ ವಿಶ್ವಾಸ",
    afternoonConfidence: "ಮಧ್ಯಾಹ್ನದ ವಿಶ್ವಾಸ",
    avgConfidenceBand: "ಸರಾಸರಿ ವಿಶ್ವಾಸ ಪಟ್ಟಿ",
    forecastAlerts: "ಮುನ್ಸೂಚನೆ ಎಚ್ಚರಿಕೆಗಳು",
    noAlerts: "ಯಾವುದೇ ಎಚ್ಚರಿಕೆಗಳಿಲ್ಲ — ಮುನ್ಸೂಚನೆ ವಿಶ್ವಾಸ ಹೆಚ್ಚಾಗಿದೆ",
    hierarchicalConsistency: "ಶ್ರೇಣೀಬದ್ಧ ಸಂಗತತೆ",
    hierarchicalSubtitle: "ಸ್ಥಾವರ ಮಟ್ಟದ ಮುನ್ಸೂಚನೆಗಳು ಕ್ಲಸ್ಟರ್ ಮಟ್ಟದ ಮುನ್ಸೂಚನೆಗಳಿಗೆ ನಿಖರವಾಗಿ ಸಮನಾಗಬೇಕು.",
    mintTitle: "ಮಿನ್ಟ್ ಸಮನ್ವಯ ನೋಟ",
    mintSubtitle: "ಮಿನ್ಟ್-ಪೂರ್ವ ಅಸಮಾನತೆಗಾಗಿ OFF, ಮಿನ್ಟ್-ನಂತರ ಸಮನ್ವಯಕ್ಕಾಗಿ ON",
    plantSum: "ಸ್ಥಾವರ ಮೊತ್ತ",
    clusterForecast: "ಕ್ಲಸ್ಟರ್ ಮುನ್ಸೂಚನೆ",
    inconsistent: "ಅಸಮಾನ — ಸ್ಥಾವರ ಮತ್ತು ಕ್ಲಸ್ಟರ್ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್‌ಗಳು ವಿರೋಧಾಭಾಸವಾಗಿವೆ",
    reconciled: "ಸಮನ್ವಯ ✓ — ಮಿನ್ಟ್ ಸಮನ್ವಯ ಅನ್ವಯಿಸಲಾಗಿದೆ",
    modelPerformance: "ಮಾದರಿ ಕಾರ್ಯಕ್ಷಮತೆ ಮೌಲ್ಯಮಾಪನ",
    modelSubtitle: "ರೋಲಿಂಗ್ ತಾತ್ಕಾಲಿಕ ಹೋಲ್ಡ್‌ಔಟ್‌ನಲ್ಲಿ ಮೌಲ್ಯಮಾಪನ ಮಾಡಲಾಗಿದೆ.",
    solarImprovement: "ಸೌರ ನ್ಮೇ ಸುಧಾರಣೆ",
    windImprovement: "ಪವನ ನ್ಮೇ ಸುಧಾರಣೆ",
    crpsImprovement: "ಸಿಆರ್‌ಪಿಎಸ್ ಸುಧಾರಣೆ",
    vsPersistence: "ತಾಳ್ಮೆ ಆಧಾರರೇಖೆ ವಿರುದ್ಧ",
    model: "ಮಾದರಿ",
    nmaeSolar: "ನ್ಮೇ ಸೌರ",
    nmaeWind: "ನ್ಮೇ ಪವನ",
    best: "ಅತ್ಯುತ್ತಮ",
    persistence: "ಮುಂದುವರಿಕೆ",
    climatological: "ಹವಾಮಾನ ಸರಾಸರಿ",
    rawNwp: "ಕಚ್ಚಾ ಎನ್‌ಡಬ್ಲ್ಯೂಪಿ ರಿಗ್ರೆಷನ್",
    ourModel: "ನಮ್ಮ ಮಾದರಿ (ಲೈಟ್‌ಜಿಬಿಎಂ + ಸಿಕ್ಯೂಆರ್)",
    dayAhead: "ದಿನ-ಮುಂದಿನ ಮುನ್ಸೂಚನೆ",
    intradayActive: "ಅಂತರ-ದಿನ ಸಕ್ರಿಯ ✓",
    lastUpdated: "ಕೊನೆಯ ನವೀಕರಣ",
    footerText: "ಎಲ್ಲಾ ಗಣನೆ ಕೆಆರ್‌ಇಡಿಎಲ್/ಕೆಎಸ್‌ಪಿಡಿಸಿಎಲ್ ಆವರಣದಲ್ಲಿ. ಕರ್ನಾಟಕ ರಾಜ್ಯ ಗಡಿಯಿಂದ ಯಾವುದೇ ಡೇಟಾ ಹೊರಹೋಗುವುದಿಲ್ಲ.",
    normalDay: "ಸಾಮಾನ್ಯ ದಿನ",
    cloudRamp: "ಮೋಡ ರ್ಯಾಂಪ್ ಘಟನೆ",
    monsoonOnset: "ಮಾನ್ಸೂನ್ ಆರಂಭ",
    windRamp: "ಗಾಳಿ ರ್ಯಾಂಪ್",
    clusterA: "ಕ್ಲಸ್ಟರ್ ಎ — ಪಾವಗಡ ಸೌರ",
    clusterB: "ಕ್ಲಸ್ಟರ್ ಬಿ — ಗದಗ ಪವನ",
    confidenceScore: "ಮುನ್ಸೂಚನೆ ವಿಶ್ವಾಸ",
    safeToSchedule: "ನಿಕಟ ವೇಳಾಪಟ್ಟಿ ಸುರಕ್ಷಿತ",
    holdReserve: "ಮೀಸಲು ಅಂಚು ಹಿಡಿದಿಡಿ",
    highUncertainty: "ಹೆಚ್ಚಿನ ಅನಿಶ್ಚಿತತೆ — ನವೀಕರಣಕ್ಕಾಗಿ ಕಾಯಿರಿ",
    carbonAvoided: "ಇಂದು ತಪ್ಪಿಸಿದ ಇಂಗಾಲ",
    estimatedSavings: "ಇಂದಿನ ಅಂದಾಜು ಉಳಿತಾಯ",
    liveData: "ನೇರ ಡೇಟಾ",
    cachedData: "ಸಂಗ್ರಹಿತ ಡೇಟಾ",
  }
}
```

Create a `src/context/LanguageContext.jsx`:

```javascript
import { createContext, useContext, useState } from 'react'
import { translations } from '../i18n/translations'

const LanguageContext = createContext()

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState('en')
  const t = (key) => translations[lang][key] || translations['en'][key] || key
  const toggleLang = () => setLang(l => l === 'en' ? 'kn' : 'en')
  return (
    <LanguageContext.Provider value={{ lang, toggleLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export const useLanguage = () => useContext(LanguageContext)
```

Wrap the entire app in `LanguageProvider` in main.jsx.

In App.jsx add a toggle button in the navbar right side, before the SystemStatus component:

```jsx
const { lang, toggleLang } = useLanguage()

<button
  onClick={toggleLang}
  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border border-[#2a2d3e] hover:border-[#3b82f6] transition-colors"
  style={{ color: '#8b8fa8' }}
>
  <span style={{ color: lang === 'kn' ? '#3b82f6' : '#8b8fa8' }}>ಕ</span>
  <span style={{ color: '#5a5d72' }}>/</span>
  <span style={{ color: lang === 'en' ? '#3b82f6' : '#8b8fa8' }}>A</span>
</button>
```

Replace every hardcoded string throughout the entire codebase with `t('key')` using the translation keys defined above. Import `useLanguage` in every component that has visible text. Every single label, badge, button text, card title, footer, alert type label — everything goes through `t()`.

The language preference should persist in localStorage so if the user refreshes the page it stays in the selected language.

---

### 2. Confidence Score 1-10 — 30 minutes

Paste this into Cursor right after:

---

Add a large confidence score display to the Plant View, positioned prominently between the plant selector controls and the IntervalStats cards. This is the single most important usability feature for non-technical operators.

Create `src/components/ConfidenceScore.jsx`:

The confidence score is computed as follows: take the average P90-P10 interval width across all 24 hours. Divide by the plant's capacity in MW. Subtract from 1. Multiply by 10. Round to one decimal. Clamp between 1 and 10. Higher score means narrower intervals means higher confidence.

```javascript
const computeConfidence = (p10, p90, capacityMw) => {
  const avgWidth = p90.reduce((sum, v, i) => sum + (v - p10[i]), 0) / p90.length
  const score = Math.max(1, Math.min(10, 10 - (avgWidth / capacityMw) * 10))
  return Math.round(score * 10) / 10
}
```

Display it as a large card spanning full width. The card shows:

Left side: the label from `t('confidenceScore')` in small uppercase muted text. Below it a massive number like "8.4" in a font size of 64px. Below the number a colored label.

Right side: a simple visual gauge — a horizontal bar divided into 10 segments. Filled segments are colored, empty segments are dark. Color scheme: segments 1-3 red, 4-6 yellow, 7-10 green.

Color and label rules:
- Score 7-10: green (#22c55e), label from `t('safeToSchedule')`
- Score 4-6: amber (#f59e0b), label from `t('holdReserve')`  
- Score 1-3: red (#ef4444), label from `t('highUncertainty')`

The score updates every time forecastData changes — including after the intraday update fires. After intraday update the score should visibly increase because the bands narrow.

---

### 3. Carbon Counter + Savings Counter — 45 minutes

Paste this into Cursor:

---

Add two metric counters to the dashboard navbar, positioned between the Live/Cached indicator and the language toggle. These display live computed values based on current forecast data.

Create `src/components/ImpactCounters.jsx`.

The component receives the current forecast data as a prop from App.jsx. App.jsx should track the latest forecast data across all plants and pass it to ImpactCounters.

**Carbon avoided calculation:**
Sum all P50 values across all plants across all 24 hours. This gives total MWh forecast for the day. Multiply by India's grid emission factor 0.82 (kg CO2 per kWh = tonnes CO2 per MWh). This gives tonnes of CO2 avoided compared to equivalent fossil generation.

Display as: `🌱 847 t CO₂` in green text, small, with label "avoided today" below in muted text.

**Savings calculation:**
Take the improvement in forecast accuracy — hardcoded as 17% improvement. Apply to spinning reserve cost. Use ₹8,000 per MW-hour as spinning reserve cost. Take total forecast MWh times 0.17 times 8000 divided by 1000 to get lakhs. 

Display as: `₹ 34.2L` in green text with label "saved today" below in muted text.

Both counters animate on mount — count up from 0 to their final value over 2 seconds using a simple setInterval animation. This makes them feel live and dynamic when the page loads or when a new plant forecast arrives.

Both counters sit in a subtle card in the navbar. On mobile they collapse to icons only. On desktop they show the full number and label.

---

### 4. Karnataka Grid Map — 3 hours

Paste this into Cursor:

---

Add a fifth navigation tab called "Grid Map" (or `t('gridMap')` in Kannada mode). Create `src/pages/GridMapView.jsx`.

Do not use any external map library. Build the Karnataka map as an inline SVG. Here is the exact SVG path for Karnataka's outline that you must use — it is a simplified but recognizable outline:

```
M 180,20 L 220,15 L 280,25 L 320,40 L 350,35 L 380,50 
L 390,80 L 400,110 L 390,140 L 410,170 L 400,200 
L 380,230 L 360,250 L 340,280 L 310,300 L 290,330 
L 270,350 L 250,370 L 220,380 L 200,360 L 180,340 
L 160,310 L 150,280 L 140,250 L 130,220 L 120,190 
L 110,160 L 120,130 L 130,100 L 150,70 L 160,45 Z
```

Fill: #1e2130, stroke: #3b82f6, strokeWidth: 1.5. The map should be centered in a dark card filling most of the page.

Plot the 6 plant locations as circles on the map using these pixel coordinates (pre-calculated for the SVG viewport):

```javascript
const plantCoordinates = {
  PVG_S1: { x: 285, y: 195, name: 'Pavagada Solar 1', type: 'solar' },
  PVG_S2: { x: 290, y: 200, name: 'Pavagada Solar 2', type: 'solar' },
  MIX_S1: { x: 265, y: 210, name: 'Chitradurga Solar', type: 'solar' },
  GAD_W1: { x: 210, y: 165, name: 'Gadag Wind 1', type: 'wind' },
  GAD_W2: { x: 215, y: 170, name: 'Gadag Wind 2', type: 'wind' },
  MIX_W1: { x: 245, y: 180, name: 'Raichur Wind', type: 'wind' },
}
```

Each plant circle has:
- Radius 12px
- Color based on confidence score: green if high confidence, yellow if medium, red if low. Use the same confidence computation from the ConfidenceScore component. Pass all forecast data as prop to GridMapView.
- A pulsing animation ring around it — same CSS pulse animation as the LIVE dot but larger, color matching the confidence color
- On hover: show a tooltip card with plant name, current P50 forecast at the current hour, confidence score, and latest alert message

Add labels for major Karnataka cities on the map for context. Bengaluru at approximately x:295, y:255. Hubli at x:195, y:175. Mysuru at x:250, y:295. Use small white text, font-size 10px, muted color.

Add a legend in the bottom left of the map:
- Green circle: High Confidence (7-10)
- Yellow circle: Medium Confidence (4-6)  
- Red circle: Low Confidence (1-3)
- Solar symbol (☀) and Wind symbol (💨) to distinguish plant types

Add a cluster boundary visualization — draw two light dashed rectangles or ellipses loosely grouping Cluster A plants and Cluster B plants. Label them "Cluster A" and "Cluster B" in small muted text.

This page should auto-refresh forecast data for all 6 plants every 60 seconds using setInterval in useEffect, so the confidence circles update automatically.

---

### 5. Digital Duty Officer Logbook — 4 hours

Paste this into Cursor:

---

Add a sixth navigation tab called "Logbook" (`t('logbook')` in Kannada mode). Create `src/pages/LogbookView.jsx`.

This replaces the government control room's physical paper logbook with a digital searchable auditable version.

**Layout: two column**

Left column (60%): The log entries list, newest first. Right column (40%): The new entry form.

**Right column — New Entry Form:**

```
[Plant selector dropdown — all 6 plants + "General / All Plants"]
[Hour selector — 00:00 to 23:00]
[Textarea — "Enter observation, action taken, or note..."]
[Duty Officer Name input]
[Submit button — "Add to Logbook"]
```

On submit: create a new log entry object:
```javascript
{
  id: Date.now(),
  timestamp: new Date().toISOString(),
  plant_id: selectedPlant,
  hour: selectedHour,
  note: noteText,
  officer: officerName,
  forecast_p50_at_hour: getCurrentP50ForHour(selectedPlant, selectedHour)
}
```

Store all entries in localStorage under key `urjadrishti_logbook`. Load on mount. Entries persist across page refreshes.

**Left column — Entries List:**

Each entry is a card showing:
- Timestamp in IST format, large, at top left
- Plant name and hour in a badge
- Officer name in small muted text  
- The note text in primary color, readable size
- Below the note in muted italic text: "Forecast at this hour was [P50 value] MW"
- A subtle delete button (trash icon) on hover only

**Top of left column:**
- Search bar — filters entries by plant, officer name, or note text in real time
- Filter dropdown — All Plants, or specific plant
- "Export as PDF" button — uses browser window.print() with a CSS print stylesheet that hides everything except the logbook entries, formats them cleanly as a printable document with the UrjaDrishti header

**Pre-populate with 5 realistic mock entries so the page doesn't look empty on first load:**

```javascript
const mockEntries = [
  {
    id: 1,
    timestamp: "2026-03-05T06:15:00.000Z",
    plant_id: "PVG_S1",
    hour: "06:00",
    note: "Morning shift started. Clear sky conditions. Forecast confidence high. Proceeding with scheduled draw.",
    officer: "R. Kumar",
    forecast_p50_at_hour: 12.3
  },
  {
    id: 2,
    timestamp: "2026-03-05T09:30:00.000Z",
    plant_id: "GAD_W1",
    hour: "09:00",
    note: "Wind speed picking up from northwest. Output tracking above forecast. No action required.",
    officer: "S. Patil",
    forecast_p50_at_hour: 45.2
  },
  {
    id: 3,
    timestamp: "2026-03-05T11:45:00.000Z",
    plant_id: "MIX_S1",
    hour: "11:00",
    note: "Cloud cover developing from west. Notified dispatch. Reduced scheduled draw by 10 MW as precaution. Will reassess at 13:00 intraday update.",
    officer: "R. Kumar",
    forecast_p50_at_hour: 67.8
  },
  {
    id: 4,
    timestamp: "2026-03-05T13:05:00.000Z",
    plant_id: "MIX_S1",
    hour: "13:00",
    note: "Intraday update received. Cloud cover confirmed. Forecast revised down 15%. Reserve margin held as planned. System performed as expected.",
    officer: "R. Kumar",
    forecast_p50_at_hour: 58.4
  },
  {
    id: 5,
    timestamp: "2026-03-05T14:00:00.000Z",
    plant_id: "GAD_W2",
    hour: "14:00",
    note: "Afternoon shift handover complete. All systems nominal. Wind cluster performing above forecast. Evening ramp expected at 17:00 per system alert.",
    officer: "M. Hegde",
    forecast_p50_at_hour: 72.1
  }
]
```

**Print stylesheet** — add to index.css:
```css
@media print {
  body * { visibility: hidden; }
  .logbook-printable, .logbook-printable * { visibility: visible; }
  .logbook-printable { position: absolute; left: 0; top: 0; width: 100%; }
  .no-print { display: none !important; }
}
```

Add class `logbook-printable` to the entries list div and `no-print` to the form column and all navigation.

The printed output should show: UrjaDrishti header, date range of entries shown, then all entries in clean readable format suitable for an audit committee.

---

### 6. Forecast Replay — 2 hours

Paste this into Cursor:

---

Add a "Yesterday's Performance" toggle to the Plant View. Position it as a small button below the IntervalStats cards, labeled "Show Yesterday's Performance" with a History icon from lucide-react.

When toggled on, overlay a second dataset on the ForecastChart showing how yesterday's forecast compared to yesterday's actuals.

Generate realistic mock "yesterday" data in the forecast mock functions. Add a function `mockYesterdayData(plantId)` that returns:

```javascript
{
  forecast: [...], // yesterday's p50 forecast for all 24 hours
  actuals: [...]   // yesterday's actual generation with slight realistic deviation from forecast
}
```

The actuals should deviate from the forecast by a random amount between -8% and +8% per hour, with a brief larger deviation around hour 11-13 simulating a partial cloud event that the forecast partially missed.

In ForecastChart add two optional props: `yesterdayForecast` and `yesterdayActuals`. When provided, overlay:
- Dashed grey line (strokeDasharray="4 4", stroke="#5a5d72", opacity 0.7) for yesterday's forecast
- Dotted line (strokeDasharray="2 4", stroke="#22c55e", opacity 0.8) for yesterday's actuals

Add a legend below the chart that appears only when yesterday mode is active:
- Solid blue/purple line: Today's forecast (P50)
- Dashed grey line: Yesterday's forecast
- Dotted green line: Yesterday's actuals
- Accuracy badge: "Yesterday: [X]% accurate — forecast within [Y] MW of actual at peak"

Compute the accuracy as: 100 minus the mean absolute percentage error between yesterdayForecast and yesterdayActuals, rounded to one decimal.

The toggle button text changes to "Hide Yesterday's Performance" when active. The chart animates the new lines in using Recharts animation.

---

### 7. Morning Briefing Email + WhatsApp — 2 hours

Paste this into Cursor after adding Twilio and SendGrid to requirements.txt:

---

Add a "Notifications" section to the dashboard. Create a small settings panel accessible from a Bell icon in the navbar.

When clicked the Bell icon opens a slide-out panel from the right side. Width 320px. Title "Alert Settings".

The panel contains:

**WhatsApp Duty Officer Alert:**
- Toggle switch to enable/disable
- Phone number input field with +91 prefix
- Threshold selector: "Alert me when confidence drops below" with options 3, 4, 5, 6
- Save button
- Status: "Last alert sent: [timestamp]" or "No alerts sent yet"

**Morning Briefing Email:**
- Toggle switch to enable/disable  
- Email input field
- Time selector defaulting to 06:00 IST
- Save button

**Test buttons:**
- "Send Test WhatsApp Now" button — calls POST /api/notifications/test-whatsapp
- "Send Test Email Now" button — calls POST /api/notifications/test-email

**Storage:** Save all notification settings to localStorage under `urjadrishti_notification_settings`.

For the backend, add these endpoints to a new file `backend/src/routes/notifications.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel
import os

router = APIRouter()

class WhatsAppRequest(BaseModel):
    phone: str
    message: str

class EmailRequest(BaseModel):
    email: str
    subject: str
    body: str

@router.post("/test-whatsapp")
def test_whatsapp(req: WhatsAppRequest):
    try:
        from twilio.rest import Client
        client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
        client.messages.create(
            from_='whatsapp:+14155238886',
            to=f'whatsapp:{req.phone}',
            body=req.message
        )
        return {"status": "sent"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.post("/test-email")
def test_email(req: EmailRequest):
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail
        sg = sendgrid.SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        mail = Mail(
            from_email="urjadrishti@kredl.karnataka.gov.in",
            to_emails=req.email,
            subject=req.subject,
            html_content=req.body
        )
        sg.send(mail)
        return {"status": "sent"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
```

Add to .env:
```
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
SENDGRID_API_KEY=your_key
```

Register the router in main.py:
```python
from src.routes import notifications
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
```

For the demo: sign up for Twilio free trial at twilio.com, verify your own phone number as the recipient, put your number in the dashboard, click "Send Test WhatsApp Now" during the presentation. The WhatsApp arrives on your phone live in front of the evaluators.

For SendGrid: sign up free at sendgrid.com, verify your email, send a test briefing email during the demo. Show it arriving in Gmail on screen.

---

### 8. Forecast Accountability Ledger — 3 hours

Paste this into Cursor last:

---

Add a "Ledger" section inside the Evaluation page as a second tab alongside the performance metrics. Tab labels: "Performance Metrics" and "Forecast Ledger".

Create `src/components/ForecastLedger.jsx`.

The ledger is a sortable filterable table showing historical forecast vs actual data.

Columns: Date, Plant, Forecast Peak (MW), Actual Peak (MW), Error (%), Duty Officer, Confidence Score at time, Notes.

Generate 14 days of realistic mock ledger data — one entry per plant per day = 84 rows. The data should show:
- Generally low errors (2-8%) on clear days
- Higher errors (10-18%) during monsoon onset days
- A few days flagged with notes like "Cloud ramp event — forecast revised intraday"
- Duty officer names rotating between R. Kumar, S. Patil, M. Hegde, A. Nair

Table features:
- Click column header to sort ascending/descending
- Search bar filtering by plant, date, or officer
- Row color coding: green if error below 5%, yellow if 5-10%, red if above 10%
- Hover on error cell shows tooltip: "Absolute error: X MW — within acceptable operational range" or "Exceeded threshold — see notes"
- "Export for Audit Committee" button using window.print()

At the bottom of the table a summary row:
- Average error across all plants and days
- Best performing plant
- Most accurate day
- "System accuracy over 14 days: X% — exceeding 85% operational target"

This table is the system's accountability record. Every row is a promise the system made and a measurement of whether it kept that promise. Government evaluators and auditors will understand this immediately.

---

## What This Looks Like When Done

Your dashboard has:

1. Plant View — forecast ribbon, confidence score, interval stats, alerts, yesterday's performance overlay, intraday simulation
2. Cluster View — stacked bar chart, reconciliation toggle
3. Evaluation — performance metrics + forecast accountability ledger
4. Grid Map — Karnataka SVG with live confidence circles on each plant
5. Logbook — digital duty officer logbook replacing paper process
6. Notifications panel — WhatsApp and email alerts settings

Language toggle switching entire UI to Kannada. Carbon counter and savings counter in the navbar. 1-10 confidence score front and center.

No other team in this hackathon will have any of these. Most teams will have a chart and a table. You have a system.

Go build it. All prompts are ready. Cursor handles the implementation. You just have to paste and review.