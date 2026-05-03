import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const client = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
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
 * Day-ahead: P10 = P50 - 25 - random(0..8), P90 = P50 + 25 + random(0..8), clamp >= 0.
 * Intraday: P10 = P50 - 10 - random(0..5), P90 = P50 + 10 + random(0..5).
 * @param {string} plantId
 * @param {{ mode: 'dayahead' | 'intraday', stressMultiplier?: number }} opts
 */
function buildSeries(plantId, opts) {
  const { capacityMw, type } = plantMeta(plantId)
  const stress = opts.stressMultiplier ?? 1
  const baseHalf = opts.mode === 'intraday' ? 10 : 25
  const randMax = opts.mode === 'intraday' ? 5 : 8

  const p50 = HOURS.map((h) =>
    type === 'solar' ? solarP50(h, capacityMw) : windP50(plantId, h, capacityMw)
  )

  const p10 = HOURS.map((h, i) => {
    const r = detRandInt(plantId, h, 11, randMax)
    const low = baseHalf * stress + r
    return Math.max(0, p50[i] - low)
  })
  const p90 = HOURS.map((h, i) => {
    const r = detRandInt(plantId, h, 19, randMax)
    const high = baseHalf * stress + r
    return Math.max(0, p50[i] + high)
  })

  return {
    plant_id: plantId,
    hours: HOURS,
    p50,
    p10,
    p90,
  }
}

/** @param {string} scenario */
function scenarioStressMultiplier(scenario) {
  if (!scenario || scenario === 'Normal Day') return 1
  return 1.45
}

export function mockForecast(plantId, scenario = 'Normal Day') {
  return buildSeries(plantId, {
    mode: 'dayahead',
    stressMultiplier: scenarioStressMultiplier(scenario),
  })
}

export function mockIntradayForecast(plantId) {
  return buildSeries(plantId, { mode: 'intraday', stressMultiplier: 1 })
}

export function mockAlerts() {
  return {
    alerts: [
      {
        hour: 10,
        message:
          'SHAP drivers indicate increased cloud cover and diffuse irradiance around mid-morning — expect a softer ramp than clear-sky baseline.',
        type: 'warning',
      },
      {
        hour: 13,
        message:
          'Conditions align with favourable generation through the midday peak — forecast confidence is elevated for this interval.',
        type: 'success',
      },
      {
        hour: 17,
        message:
          'Evening transition introduces rising forecast uncertainty as boundary-layer dynamics become less constrained by observations.',
        type: 'info',
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

export function formatMw(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '0.0'
  return n.toFixed(1)
}

/**
 * @param {string} plantId
 * @param {number} hoursOfActuals
 * @param {string} [scenario]
 */
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

/**
 * @param {string} plantId
 * @param {number[]} actuals
 */
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

/**
 * @param {string} plantId
 * @param {number[]} p50
 * @param {number[]} hours
 */
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

export async function fetchReconciled() {
  try {
    const { data } = await client.get('/api/reconciled/')
    return { data, usedFallback: false, error: null }
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

export function plantsInCluster(cluster) {
  return PLANTS.filter((p) => p.cluster === cluster)
}
