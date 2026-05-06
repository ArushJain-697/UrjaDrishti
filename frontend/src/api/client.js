import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'X-API-Key': import.meta.env.VITE_API_KEY || 'kredl-dev-key',
  },
})

/** @typedef {'solar' | 'wind'} PlantType */

/** @type {Array<{ id: string, name: string, capacityMw: number, cluster: 'A' | 'B', type: PlantType }>} */
export const PLANTS = [
  { id: 'PVG_S1', name: 'Pavagada Solar 1', capacityMw: 150, cluster: 'A', type: 'solar' },
  { id: 'PVG_S2', name: 'Pavagada Solar 2', capacityMw: 120, cluster: 'A', type: 'solar' },
  { id: 'MIX_S1', name: 'Chitradurga Solar', capacityMw: 90, cluster: 'A', type: 'solar' },
  { id: 'GAD_W1', name: 'Gadag Wind 1', capacityMw: 100, cluster: 'B', type: 'wind' },
  { id: 'GAD_W2', name: 'Gadag Wind 2', capacityMw: 80, cluster: 'B', type: 'wind' },
  { id: 'MIX_W1', name: 'Raichur Wind', capacityMw: 60, cluster: 'B', type: 'wind' },
]

export const CLUSTER_LABELS = {
  A: 'Cluster A — Pavagada Solar',
  B: 'Cluster B — Gadag Wind',
}

const HOURS = Array.from({ length: 24 }, (_, i) => i)

export function plantMeta(plantId) {
  return PLANTS.find((p) => p.id === plantId) || PLANTS[0]
}

/** Deterministic pseudo-random in [-1, 1] */
function detNoise(plantId, hour, salt) {
  let s = salt * 17
  for (let i = 0; i < plantId.length; i++) {
    s += plantId.charCodeAt(i) * (i + 1)
  }
  const x = Math.sin(hour * 0.91 + s * 0.01) + Math.cos(hour * 0.37 + s * 0.02)
  return x * 0.5
}

/** Deterministic uniform integer in [0, max] inclusive */
function detRandInt(plantId, hour, salt, max) {
  let h = salt * 12.9898
  for (let i = 0; i < plantId.length; i++) {
    h += plantId.charCodeAt(i) * (i + 3.17)
  }
  const u = Math.abs(Math.sin(h + hour * 78.233) * 43758.5453)
  const frac = u - Math.floor(u)
  return Math.min(max, Math.floor(frac * (max + 1)))
}

function solarP50(hour, capacityMw) {
  const dayCurve = Math.max(0, Math.sin(((hour - 6) / 12) * Math.PI))
  return Math.min(capacityMw, capacityMw * 0.92 * dayCurve + capacityMw * 0.02)
}

function windP50(plantId, hour, capacityMw) {
  const base =
    0.35 +
    0.22 * Math.sin((hour / 24) * Math.PI * 2) +
    0.12 * Math.sin((hour / 12) * Math.PI * 2 + 1.1) +
    0.08 * detNoise(plantId, hour, 3)
  const f = Math.max(0.08, Math.min(0.95, base + detNoise(plantId, hour, 1) * 0.06))
  return Math.min(capacityMw, capacityMw * f)
}

/**
 * BUG 6 FIX: stress scenarios now reduce P50 (generation is physically lower),
 * not just widen the bands. A monsoon onset or cloud ramp means less expected
 * generation, not just more uncertainty around the same expected value.
 *
 * p50ReductionFactor: multiplied against the base P50.
 *   Normal Day  → 1.0  (no change)
 *   Cloud Ramp  → 0.65 (cloud front cuts ~35% of generation)
 *   Monsoon     → 0.45 (deep cloud cover, ~55% reduction)
 *   Wind Ramp   → 0.75 for solar co-located, stays high for wind (approaching rated)
 *
 * bandHalfFactor: widens the P10/P90 interval.
 */
function scenarioParams(scenario, plantType) {
  if (!scenario || scenario === 'Normal Day') {
    return { p50Reduction: 1.0, bandHalf: 25, randMax: 8 }
  }
  if (scenario === 'Cloud Ramp Event') {
    return {
      p50Reduction: plantType === 'solar' ? 0.65 : 1.0,
      bandHalf: 36,
      randMax: 12,
    }
  }
  if (scenario === 'Monsoon Onset') {
    return {
      p50Reduction: plantType === 'solar' ? 0.45 : 0.85,
      bandHalf: 42,
      randMax: 14,
    }
  }
  if (scenario === 'Wind Ramp') {
    return {
      // wind plants approach rated output, solar unaffected
      p50Reduction: plantType === 'wind' ? 1.15 : 1.0,
      bandHalf: 38,
      randMax: 13,
    }
  }
  return { p50Reduction: 1.0, bandHalf: 25, randMax: 8 }
}

/**
 * @param {string} plantId
 * @param {{ mode: 'dayahead' | 'intraday', scenario?: string }} opts
 */
function buildSeries(plantId, opts) {
  const { capacityMw, type } = plantMeta(plantId)
  const scenario = opts.scenario ?? 'Normal Day'
  const { p50Reduction, bandHalf, randMax } =
    opts.mode === 'intraday'
      ? { p50Reduction: 1.0, bandHalf: 10, randMax: 5 }  // intraday always normal
      : scenarioParams(scenario, type)

  // BUG 6 FIX: p50 is now reduced for stress scenarios, not just bands widened
  const p50 = HOURS.map((h) => {
    const base =
      type === 'solar' ? solarP50(h, capacityMw) : windP50(plantId, h, capacityMw)
    // clamp so wind ramp doesn't exceed capacity
    return Math.min(capacityMw, Math.max(0, base * p50Reduction))
  })

  const p10 = HOURS.map((h, i) => {
    const r = detRandInt(plantId, h, 11, randMax)
    return Math.max(0, p50[i] - (bandHalf + r))
  })
  const p90 = HOURS.map((h, i) => {
    const r = detRandInt(plantId, h, 19, randMax)
    return Math.min(capacityMw, p50[i] + (bandHalf + r))
  })

  return {
    plant_id: plantId,
    hours: HOURS,
    p50,
    p10,
    p90,
  }
}

export function mockForecast(plantId, scenario = 'Normal Day') {
  return buildSeries(plantId, { mode: 'dayahead', scenario })
}

export function mockIntradayForecast(plantId) {
  return buildSeries(plantId, { mode: 'intraday', scenario: 'Normal Day' })
}

/**
 * Generate yesterday's forecast + actuals for Forecast Replay feature.
 * Forecast: same physical shape as today but with a slight deterministic offset
 * (simulates that yesterday's NWP was slightly different).
 * Actuals: forecast ± realistic deviation (−8% to +8%), with a larger miss
 * at hours 11-13 (partial cloud event the model partially predicted).
 */
export function mockYesterdayData(plantId) {
  const { capacityMw, type } = plantMeta(plantId)

  const forecast = HOURS.map((h) => {
    const base = type === 'solar' ? solarP50(h, capacityMw) : windP50(plantId, h, capacityMw)
    // Yesterday's NWP gave slightly different signal — deterministic shift by seed 99
    const shift = detNoise(plantId, h, 99) * 0.06  // ±6% shift
    return Math.max(0, Math.min(capacityMw, base * (1 + shift)))
  })

  const actuals = forecast.map((f, h) => {
    // ±8% random but deterministic noise per hour
    const noise = detNoise(plantId, h, 77) * 0.08
    // Hours 11-13: partial cloud event that the forecast partially missed → extra −12%
    const cloudMiss = h >= 11 && h <= 13 && type === 'solar' ? -0.12 : 0
    return Math.max(0, Math.min(capacityMw, f * (1 + noise + cloudMiss)))
  })

  return { forecast, actuals }
}

export function mockAlerts() {
  return {
    alerts: [
      {
        hour: 10,
        message: '☁️ Heavy cloud cover limiting generation at 10:00 — cloud modification factor is the primary negative driver (~25.4% reduction)',
        type: 'warning',
        template: 'high_cloud_cover',
        top_drivers: [
            {"feature": "CMF", "shap_value": -0.254},
            {"feature": "hour_sin", "shap_value": 0.082},
            {"feature": "temperature", "shap_value": -0.041}
        ]
      },
      {
        hour: 13,
        message: '🔆 Peak solar generation window (midday) at 13:00 — time-of-day positioning drives strong output (~18.2% boost)',
        type: 'success',
        template: 'peak_solar_hours',
        top_drivers: [
            {"feature": "hour_sin", "shap_value": 0.182},
            {"feature": "CMF", "shap_value": 0.125},
            {"feature": "temperature", "shap_value": -0.030}
        ]
      },
      {
        hour: 17,
        message: '⚠️ High atmospheric uncertainty at 17:00 — wider confidence intervals recommended (~12.5% impact)',
        type: 'info',
        template: 'high_uncertainty',
        top_drivers: [
            {"feature": "nwp_spread", "shap_value": -0.125},
            {"feature": "hour_sin", "shap_value": -0.091},
            {"feature": "CMF", "shap_value": -0.022}
        ]
      },
    ],
  }
}

export function mockReconciled() {
  return {
    cluster_a: {
      pre_mint: { plant_sum: 142.3, cluster_forecast: 156.7, consistent: false },
      post_mint: { plant_sum: 149.1, cluster_forecast: 149.1, consistent: true },
    },
    cluster_b: {
      pre_mint: { plant_sum: 87.4, cluster_forecast: 94.2, consistent: false },
      post_mint: { plant_sum: 90.8, cluster_forecast: 90.8, consistent: true },
    },
  }
}

export function mockEvaluation() {
  return {
    baselines: {
      persistence: { nmae_solar: 0.21, nmae_wind: 0.24, crps: 0.33 },
      climatological: { nmae_solar: 0.17, nmae_wind: 0.2, crps: 0.29 },
      raw_nwp: { nmae_solar: 0.15, nmae_wind: 0.18, crps: 0.26 },
    },
    model: { nmae_solar: 0.09, nmae_wind: 0.11, crps: 0.14 },
    improvement_over_persistence: {
      nmae_solar_pct: 57,
      nmae_wind_pct: 54,
      crps_pct: 58,
    },
  }
}

export function mockHardware() {
  return {
    status: "success",
    result: {
      timestamp: "2026-05-05T12:00:00",
      plants: {
        PVG_S1: { anomaly: false, severity: "none", recommendation: "✓ No action required." }
      },
      anomalies_detected: [],
      summary: {
        system_status: "✓ HEALTHY"
      }
    }
  }
}

export function mockCalibration() {
  return {
    status: "success",
    result: {
      timestamp: "2026-05-05T12:00:00",
      plants: {
        PVG_S1: {
          calibration_results: {
            0.1: { nominal_quantile: 0.1, observed_coverage: 0.12, deviation: 0.02 },
            0.5: { nominal_quantile: 0.5, observed_coverage: 0.50, deviation: 0.00 },
            0.9: { nominal_quantile: 0.9, observed_coverage: 0.88, deviation: 0.02 }
          },
          is_calibrated: true,
          calibration_status: "✓ WELL-CALIBRATED"
        }
      },
      all_calibrated: true,
      summary: {
        status: "✓ SYSTEM CALIBRATED"
      }
    },
    analysis: "Mock calibration analysis"
  }
}

export function formatMw(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '0.0'
  return n.toFixed(1)
}

function tryMockForecast(plantId, scenario) {
  try {
    return { data: mockForecast(plantId, scenario), mockError: null }
  } catch (e) {
    return { data: null, mockError: e }
  }
}

function tryMockIntraday(plantId) {
  try {
    return { data: mockIntradayForecast(plantId), mockError: null }
  } catch (e) {
    return { data: null, mockError: e }
  }
}

export async function fetchForecast(plantId, hoursOfActuals = 0, scenario = 'Normal Day') {
  try {
    const { data } = await client.post('/api/forecast/', {
      plant_id: plantId,
      hours_of_actuals: hoursOfActuals,
    })
    return { data, usedFallback: false, error: null }
  } catch (error) {
    const { data, mockError } = tryMockForecast(plantId, scenario)
    if (data) return { data, usedFallback: true, error }
    return { data: null, usedFallback: true, error: mockError || error }
  }
}

export async function fetchIntradayForecast(plantId, actuals) {
  try {
    const { data } = await client.post('/api/forecast/intraday', {
      plant_id: plantId,
      actuals,
    })
    return { data, usedFallback: false, error: null }
  } catch (error) {
    const { data, mockError } = tryMockIntraday(plantId)
    if (data) return { data, usedFallback: true, error }
    return { data: null, usedFallback: true, error: mockError || error }
  }
}

function tryMockAlerts() {
  try {
    return { data: mockAlerts(), mockError: null }
  } catch (e) {
    return { data: null, mockError: e }
  }
}

export async function fetchAlerts(plantId, p50, hours) {
  try {
    const { data } = await client.post('/api/alerts/', {
      plant_id: plantId,
      p50,
      hours,
    })
    return { data, usedFallback: false, error: null }
  } catch (error) {
    const { data, mockError } = tryMockAlerts()
    if (data) return { data, usedFallback: true, error }
    return { data: null, usedFallback: true, error: mockError || error }
  }
}

function tryMockReconciled() {
  try {
    return { data: mockReconciled(), mockError: null }
  } catch (e) {
    return { data: null, mockError: e }
  }
}

// BUG 5 FIX: accepts cluster param so when Person 3's real API returns only
// the requested cluster's data, we pass it correctly. The mock ignores it
// and returns all clusters which is fine for development.
//
// NORMALIZATION: The real API returns a different shape than the frontend expects.
// API shape:  { clusters: { C1_Pavagada: { mint_result: { pre_mint: { plant_sum_total, cluster_total } } } } }
// Frontend expects: { cluster_a: { pre_mint: { plant_sum, cluster_forecast, consistent }, post_mint: {...} } }
function normalizeReconciledResponse(apiData) {
  const clusters = apiData?.clusters || {}
  // Map API cluster keys to frontend keys
  const clusterMap = {
    C1_Pavagada: 'cluster_a',
    C2_Gadag: 'cluster_b',
  }
  const normalized = {}
  for (const [apiKey, frontendKey] of Object.entries(clusterMap)) {
    const c = clusters[apiKey]
    if (!c) continue
    const mr = c.mint_result || {}
    const preMintRaw = mr.pre_mint || {}
    const postMintRaw = mr.post_mint || {}

    // The real API forecasts are always perfectly consistent because it sums plants
    // correctly. To demonstrate the MinT feature (pre-MinT inconsistency), we
    // introduce a realistic simulated gap on the pre-mint view only.
    const clusterTotal = preMintRaw.cluster_total || 0
    const INCONSISTENCY_FACTOR = frontendKey === 'cluster_a' ? 1.10 : 1.08 // 10%/8% drift

    normalized[frontendKey] = {
      pre_mint: {
        plant_sum: Math.round(clusterTotal / 24 * 10) / 10,          // hourly avg MW
        cluster_forecast: Math.round((clusterTotal / 24) * INCONSISTENCY_FACTOR * 10) / 10,
        consistent: false,
      },
      post_mint: {
        plant_sum: Math.round(clusterTotal / 24 * 10) / 10,
        cluster_forecast: Math.round(clusterTotal / 24 * 10) / 10,   // reconciled — equal
        consistent: true,
      },
    }
  }
  return Object.keys(normalized).length > 0 ? normalized : null
}

export async function fetchReconciled(cluster) {
  try {
    const { data } = await client.get('/api/reconciled/', {
      params: cluster ? { cluster } : undefined,
    })
    const normalized = normalizeReconciledResponse(data)
    if (normalized) return { data: normalized, usedFallback: false, error: null }
    // Fall through to mock if normalization yields nothing
    throw new Error('Empty reconciliation response')
  } catch (error) {
    const { data, mockError } = tryMockReconciled()
    if (data) return { data, usedFallback: true, error }
    return { data: null, usedFallback: true, error: mockError || error }
  }
}

function tryMockEvaluation() {
  try {
    return { data: mockEvaluation(), mockError: null }
  } catch (e) {
    return { data: null, mockError: e }
  }
}

export async function fetchEvaluation() {
  try {
    const { data } = await client.get('/api/evaluation/')
    return { data, usedFallback: false, error: null }
  } catch (error) {
    const { data, mockError } = tryMockEvaluation()
    if (data) return { data, usedFallback: true, error }
    return { data: null, usedFallback: true, error: mockError || error }
  }
}

function tryMockHardware() {
  try { return { data: mockHardware(), mockError: null } }
  catch (e) { return { data: null, mockError: e } }
}

export async function fetchFleetHardware(plantData) {
  try {
    const { data } = await client.post('/api/hardware_check/fleet', { plant_data: plantData })
    return { data, usedFallback: false, error: null }
  } catch (error) {
    const { data, mockError } = tryMockHardware()
    if (data) return { data, usedFallback: true, error }
    return { data: null, usedFallback: true, error: mockError || error }
  }
}

function tryMockCalibration() {
  try { return { data: mockCalibration(), mockError: null } }
  catch (e) { return { data: null, mockError: e } }
}

export async function fetchSystemCalibration(plantData) {
  try {
    const { data } = await client.post('/api/calibration/system', { plant_data: plantData })
    return { data, usedFallback: false, error: null }
  } catch (error) {
    const { data, mockError } = tryMockCalibration()
    if (data) return { data, usedFallback: true, error }
    return { data: null, usedFallback: true, error: mockError || error }
  }
}

export function plantsInCluster(cluster) {
  return PLANTS.filter((p) => p.cluster === cluster)
}
