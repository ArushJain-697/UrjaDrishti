import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'
import {
  fetchForecast,
  fetchIntradayForecast,
  formatMw,
  plantMeta,
} from '../api/client'
import PlantSelector from '../components/PlantSelector.jsx'
import IntervalStats from '../components/IntervalStats.jsx'
import ForecastChart from '../components/ForecastChart.jsx'
import AlertPanel from '../components/AlertPanel.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ServiceErrorBanner from '../components/ServiceErrorBanner.jsx'
import DataNote from '../components/DataNote.jsx'

const SCENARIOS = [
  'Normal Day',
  'Cloud Ramp Event',
  'Monsoon Onset',
  'Wind Ramp',
]

function widenUncertainty(forecast, factor) {
  if (!forecast || factor <= 1) return forecast
  const { hours, p50, p10, p90 } = forecast
  return {
    ...forecast,
    p10: hours.map((_, i) => {
      const low = p50[i] - p10[i]
      return Math.max(0, p50[i] - low * factor)
    }),
    p90: hours.map((_, i) => {
      const high = p90[i] - p50[i]
      return Math.max(0, p50[i] + high * factor)
    }),
  }
}

function scenarioFactor(scenario) {
  if (!scenario || scenario === 'Normal Day') return 1
  return 1.45
}

export default function PlantView() {
  const [selectedPlant, setSelectedPlant] = useState('PVG_S1')
  const [rawForecast, setRawForecast] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [forecastError, setForecastError] = useState(null)
  const [forecastUsedMock, setForecastUsedMock] = useState(false)
  const [isIntradayMode, setIsIntradayMode] = useState(false)
  const [isIntradayLoading, setIsIntradayLoading] = useState(false)
  const [activeScenario, setActiveScenario] = useState('Normal Day')
  const [lastUpdated, setLastUpdated] = useState(null)

  const displayForecast = useMemo(() => {
    if (!rawForecast) return null
    return widenUncertainty(rawForecast, scenarioFactor(activeScenario))
  }, [rawForecast, activeScenario])

  const loadForecast = useCallback(async () => {
    setIsLoading(true)
    setForecastError(null)
    const res = await fetchForecast(selectedPlant, 0, activeScenario)
    setRawForecast(res.data)
    setForecastUsedMock(res.usedMock)
    setForecastError(res.error)
    setLastUpdated(new Date())
    setIsLoading(false)
  }, [selectedPlant, activeScenario])

  useEffect(() => {
    setIsIntradayMode(false)
  }, [selectedPlant])

  useEffect(() => {
    loadForecast()
  }, [loadForecast])

  const onIntraday = async () => {
    if (!rawForecast?.p50?.length) return
    setIsIntradayLoading(true)
    const actuals = rawForecast.p50.slice(0, 6)
    const res = await fetchIntradayForecast(selectedPlant, actuals)
    setRawForecast(res.data)
    setForecastUsedMock(res.usedMock)
    setForecastError(res.error)
    setIsIntradayMode(true)
    setLastUpdated(new Date())
    setIsIntradayLoading(false)
  }

  const meta = plantMeta(selectedPlant)
  const intradayNowHour = isIntradayMode ? 6 : null

  return (
    <div className="mx-auto max-w-[1400px] px-4 pb-8 pt-6">
      {forecastUsedMock && forecastError ? (
        <div className="mb-4">
          <ServiceErrorBanner onRetry={loadForecast} />
        </div>
      ) : null}

      <div className="flex flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-end lg:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <PlantSelector value={selectedPlant} onChange={setSelectedPlant} />
          <div className="min-w-[200px]">
            <label htmlFor="scenario" className="sr-only">
              Scenario
            </label>
            <select
              id="scenario"
              value={activeScenario}
              onChange={(e) => setActiveScenario(e.target.value)}
              className="w-full cursor-pointer rounded-lg border border-[#2a2d3e] bg-[#1e2130] px-3 py-2 text-sm text-[#e8eaf0] outline-none transition hover:border-[#3b82f6]/40 focus:border-[#3b82f6]"
            >
              {SCENARIOS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>
        <button
          type="button"
          disabled={isIntradayLoading || isLoading || !rawForecast}
          onClick={onIntraday}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#3b82f6] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#2563eb] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isIntradayLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Recalibrating…
            </>
          ) : (
            <>
              <RefreshCw className="h-4 w-4" aria-hidden />
              Simulate Intraday Update
            </>
          )}
        </button>
      </div>

      {activeScenario !== 'Normal Day' ? (
        <div className="mt-3 rounded-lg border border-[#f59e0b]/40 bg-[#f59e0b]/10 px-3 py-2 text-[13px] text-[#fbbf24]">
          ⚠ Stress scenario active: {activeScenario} — uncertainty intervals are wider than normal
        </div>
      ) : null}

      <div className="mt-6 flex flex-col gap-6 lg:flex-row">
        <div className="w-full min-w-0 lg:w-[65%]">
          <IntervalStats
            p10={displayForecast?.p10 ?? []}
            p90={displayForecast?.p90 ?? []}
          />
          <div className="relative mt-4">
            {displayForecast ? (
              <div className={isLoading ? 'opacity-40 transition-opacity' : 'opacity-100'}>
                <ForecastChart
                  forecast={displayForecast}
                  plantId={selectedPlant}
                  intradayNowHour={intradayNowHour}
                />
              </div>
            ) : (
              <div className="flex h-[320px] items-center justify-center rounded-xl border border-[#2a2d3e] bg-[#1e2130]">
                <LoadingSpinner />
              </div>
            )}
            {isLoading && displayForecast ? (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                <LoadingSpinner size={48} />
              </div>
            ) : null}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px] text-[#8b8fa8]">
            <span>
              Last updated:{' '}
              {lastUpdated
                ? lastUpdated.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
                : '—'}
            </span>
            <span
              className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                isIntradayMode
                  ? 'bg-[#f59e0b]/15 text-[#fbbf24]'
                  : 'bg-[#1a1d27] text-[#8b8fa8]'
              }`}
            >
              {isIntradayMode ? 'Intraday update active' : 'Day-ahead forecast'}
            </span>
            {isIntradayMode ? (
              <span className="rounded-full bg-[#f59e0b]/15 px-2 py-0.5 text-[11px] font-medium text-[#fbbf24]">
                Intraday active
              </span>
            ) : null}
            <span className="text-[#5a5d72]">
              {meta.name} · {formatMw(meta.capacityMw)} MW ({meta.type})
            </span>
          </div>
        </div>
        <div className="w-full min-w-0 lg:w-[35%]">
          <AlertPanel
            plantId={selectedPlant}
            p50={displayForecast?.p50 ?? []}
            hours={displayForecast?.hours ?? []}
          />
        </div>
      </div>

      <DataNote />
    </div>
  )
}
