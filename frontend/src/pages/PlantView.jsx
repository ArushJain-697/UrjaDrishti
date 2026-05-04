import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { History, Loader2, RefreshCw } from 'lucide-react'
import {
  fetchForecast,
  fetchIntradayForecast,
  formatMw,
  mockYesterdayData,
  plantMeta,
} from '../api/client'
import PlantSelector from '../components/PlantSelector.jsx'
import IntervalStats from '../components/IntervalStats.jsx'
import ForecastChart from '../components/ForecastChart.jsx'
import AlertPanel from '../components/AlertPanel.jsx'
import ShapDrivers from '../components/ShapDrivers.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ServiceErrorBanner from '../components/ServiceErrorBanner.jsx'
import CachedDataNotice from '../components/CachedDataNotice.jsx'
import DataNote from '../components/DataNote.jsx'
import ConfidenceScore from '../components/ConfidenceScore.jsx'
import { useLanguage } from '../context/LanguageContext.jsx'

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
  const { t } = useLanguage()
  const [selectedPlant, setSelectedPlant] = useState('PVG_S1')
  const [rawForecast, setRawForecast] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [forecastError, setForecastError] = useState(null)
  const [forecastUsedFallback, setForecastUsedFallback] = useState(false)
  const [cacheNoticeKey, setCacheNoticeKey] = useState(0)
  const [isIntradayMode, setIsIntradayMode] = useState(false)
  const [isIntradayLoading, setIsIntradayLoading] = useState(false)
  const [activeScenario, setActiveScenario] = useState('Normal Day')
  const [lastUpdated, setLastUpdated] = useState(null)
  const [alertsData, setAlertsData] = useState([])
  const [showYesterday, setShowYesterday] = useState(false)

  // BUG 4 FIX: keep a stable ref to the original day-ahead forecast so that
  // repeated intraday clicks always use the same 6 actuals and don't compound drift.
  const dayAheadRef = useRef(null)

  const scenarios = useMemo(
    () => [
      { value: 'Normal Day', label: t('normalDay') },
      { value: 'Cloud Ramp Event', label: t('cloudRamp') },
      { value: 'Monsoon Onset', label: t('monsoonOnset') },
      { value: 'Wind Ramp', label: t('windRamp') },
    ],
    [t]
  )

  // FIX 6: Only apply widenUncertainty when data came from the real API.
  // The mock fallback (buildSeries in client.js) already applies scenario
  // band-widening internally — applying it a second time here would double
  // the interval width for stress scenarios.
  const displayForecast = useMemo(() => {
    if (!rawForecast) return null
    if (forecastUsedFallback) return rawForecast
    return widenUncertainty(rawForecast, scenarioFactor(activeScenario))
  }, [rawForecast, activeScenario, forecastUsedFallback])

  const loadForecast = useCallback(async () => {
    setIsLoading(true)
    setForecastError(null)
    const res = await fetchForecast(selectedPlant, 0, activeScenario)
    setRawForecast(res.data)
    // BUG 4 FIX: store original day-ahead result in ref for intraday actuals
    dayAheadRef.current = res.data
    setForecastUsedFallback(res.usedFallback)
    setForecastError(res.error)
    setLastUpdated(new Date())
    setIsLoading(false)
    if (res.data && res.usedFallback && res.error) setCacheNoticeKey((k) => k + 1)
  }, [selectedPlant, activeScenario])

  useEffect(() => {
    setIsIntradayMode(false)
  }, [selectedPlant])

  useEffect(() => {
    loadForecast()
  }, [loadForecast])

  const onIntraday = async () => {
    // BUG 4 FIX: always slice actuals from the original day-ahead ref,
    // not from rawForecast which may already be a previous intraday result.
    const sourceForActuals = dayAheadRef.current ?? rawForecast
    if (!sourceForActuals?.p50?.length) return
    setIsIntradayLoading(true)
    const actuals = sourceForActuals.p50.slice(0, 6)
    const res = await fetchIntradayForecast(selectedPlant, actuals)
    setRawForecast(res.data)
    setForecastUsedFallback(res.usedFallback)
    setForecastError(res.error)
    setIsIntradayMode(true)
    setLastUpdated(new Date())
    setIsIntradayLoading(false)
    if (res.data && res.usedFallback && res.error) setCacheNoticeKey((k) => k + 1)
  }

  const meta = plantMeta(selectedPlant)
  const intradayNowHour = isIntradayMode ? 6 : null

  return (
    <div className="mx-auto max-w-[1400px] px-4 pb-8 pt-6">
      {!rawForecast && forecastError ? (
        <div className="mb-4">
          <ServiceErrorBanner onRetry={loadForecast} />
        </div>
      ) : null}
      {rawForecast && forecastUsedFallback && forecastError ? (
        <CachedDataNotice key={cacheNoticeKey} />
      ) : null}

      <div className="flex flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-end lg:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <PlantSelector value={selectedPlant} onChange={setSelectedPlant} />
          <div className="min-w-[200px]">
            <label htmlFor="scenario" className="sr-only">
              {t('highUncertainty')}
            </label>
            <select
              id="scenario"
              value={activeScenario}
              onChange={(e) => setActiveScenario(e.target.value)}
              className="w-full cursor-pointer rounded-lg border border-line bg-hover-bg px-3 py-2 text-sm text-main-text outline-none transition hover:border-[#10b981] transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_10px_rgba(16,185,129,0.2)]/40 focus:border-[#10b981]"
            >
              {scenarios.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <button
          type="button"
          disabled={isIntradayLoading || isLoading || !rawForecast}
          onClick={onIntraday}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#10b981] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#2563eb] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isIntradayLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              {t('recalibrating')}
            </>
          ) : (
            <>
              <RefreshCw className="h-4 w-4" aria-hidden />
              {t('simulateIntraday')}
            </>
          )}
        </button>
      </div>

      {activeScenario !== 'Normal Day' ? (
        <div className="mt-3 rounded-lg border border-[#f59e0b]/40 bg-[#f59e0b]/10 px-3 py-2 text-[13px] text-[#fbbf24]">
          ⚠ {t('highUncertainty')}: {scenarios.find((s) => s.value === activeScenario)?.label}
        </div>
      ) : null}

      <ConfidenceScore
        p10={displayForecast?.p10 ?? []}
        p90={displayForecast?.p90 ?? []}
        capacityMw={meta.capacityMw}
      />

      <div className="mt-6 flex flex-col gap-6 lg:flex-row">
        <div className="w-full min-w-0 lg:w-[65%]">
          <IntervalStats
            p10={displayForecast?.p10 ?? []}
            p90={displayForecast?.p90 ?? []}
          />
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              onClick={() => setShowYesterday((v) => !v)}
              disabled={!displayForecast}
              className="inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-[12px] font-medium text-muted-text transition-all duration-200 hover:border-[#10b981] hover:text-[#10b981] disabled:opacity-40"
            >
              <History className="h-3.5 w-3.5" aria-hidden />
              {showYesterday ? "Hide Yesterday's Performance" : "Show Yesterday's Performance"}
            </button>
          </div>
          <div className="relative mt-4">
            {displayForecast ? (
              <div className={isLoading ? 'opacity-40 transition-opacity' : 'opacity-100'}>
                <ForecastChart
                  forecast={displayForecast}
                  plantId={selectedPlant}
                  intradayNowHour={intradayNowHour}
                  yesterdayForecast={showYesterday ? mockYesterdayData(selectedPlant).forecast : null}
                  yesterdayActuals={showYesterday ? mockYesterdayData(selectedPlant).actuals : null}
                />
              </div>
            ) : (
              <div className="flex h-[320px] items-center justify-center rounded-xl border border-line bg-hover-bg">
                <LoadingSpinner />
              </div>
            )}
            {isLoading && displayForecast ? (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                <LoadingSpinner size={48} />
              </div>
            ) : null}
          </div>
          
          <ShapDrivers alerts={alertsData} />

          <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px] text-muted-text">
            <span>
              {t('lastUpdated')}:{' '}
              {lastUpdated
                ? lastUpdated.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
                : '—'}
            </span>
            <span className="inline-flex items-center gap-2">
              <span className="rounded-full bg-surface-bg px-2 py-0.5 text-[11px] font-medium text-muted-text">
                {t('dayAhead')}
              </span>
              {isIntradayMode ? (
                <span className="rounded-full bg-[#f59e0b]/15 px-2 py-0.5 text-[11px] font-medium text-[#fbbf24]">
                  {t('intradayActive')}
                </span>
              ) : null}
            </span>
            <span className="text-faint-text">
              {meta.name} · {formatMw(meta.capacityMw)} MW ({meta.type})
            </span>
          </div>
        </div>
        <div className="w-full min-w-0 lg:w-[35%]">
          {/* FIX 7: Memoize stable array refs so AlertPanel's useCallback
              doesn't see new array identities on every parent render
              (e.g. from the IST clock tick in SystemStatus), which would
              otherwise trigger an infinite fetch loop. */}
          <AlertPanel
            plantId={selectedPlant}
            p50={useMemo(() => displayForecast?.p50 ?? [], [displayForecast])}
            hours={useMemo(() => displayForecast?.hours ?? [], [displayForecast])}
            onAlertsLoaded={setAlertsData}
          />
        </div>
      </div>

      <DataNote />
    </div>
  )
}
