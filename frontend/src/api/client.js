import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000,
})

export const getForecast = (plantId) =>
  client.post('/api/forecast/', { plant_id: plantId, hours_of_actuals: 0 })

export const getIntradayForecast = (plantId, actuals) =>
  client.post('/api/forecast/intraday', { plant_id: plantId, actuals })

export const getAlerts = (plantId, p50, hours) =>
  client.post('/api/alerts/', { plant_id: plantId, p50, hours })

export const getEvaluation = () =>
  client.get('/api/evaluation/')

export const getReconciled = () =>
  client.get('/api/reconciled/')