import { useCallback, useEffect, useState } from 'react'
import { BarChart2, ClipboardList, Info, TrendingUp, Activity, Download } from 'lucide-react'
import { fetchEvaluation } from '../api/client'
import StatCard from '../components/StatCard.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ServiceErrorBanner from '../components/ServiceErrorBanner.jsx'
import CachedDataNotice from '../components/CachedDataNotice.jsx'
import DataNote from '../components/DataNote.jsx'
import ForecastLedger from '../components/ForecastLedger.jsx'
import ModelHealthPanel from '../components/ModelHealthPanel.jsx'
import { useLanguage } from '../context/LanguageContext.jsx'
import { generateReport } from '../utils/pdfGenerator.js'

function fmtMetric(x) {
  if (x == null || !Number.isFinite(Number(x))) return '—'
  return Number(x).toFixed(2)
}

function improvementColor(pct) {
  const p = Math.min(100, Math.max(0, pct))
  const saturation = 55 + p * 0.35
  const lightness = 42 - p * 0.08
  return `hsl(142, ${saturation}%, ${lightness}%)`
}

export default function EvaluationView() {
  const { t } = useLanguage()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [usedFallback, setUsedFallback] = useState(false)
  const [error, setError] = useState(null)
  const [cacheNoticeKey, setCacheNoticeKey] = useState(0)
  const [activeTab, setActiveTab] = useState('metrics')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    const res = await fetchEvaluation()
    setData(res.data)
    setUsedFallback(res.usedFallback)
    setError(res.error)
    setLoading(false)
    if (res.data && res.usedFallback && res.error) setCacheNoticeKey((k) => k + 1)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (loading && !data) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center px-4">
        <LoadingSpinner />
      </div>
    )
  }

  const imp = data?.improvement_over_persistence
  const baselines = data?.baselines
  const model = data?.model

  const rows = [
    {
      name: t('persistence'),
      key: 'persistence',
      rowClass: 'text-[#ef4444]',
      headerBadge: null,
    },
    {
      name: t('climatological'),
      key: 'climatological',
      rowClass: 'text-[#fb923c]',
      headerBadge: null,
    },
    {
      name: t('rawNwp'),
      key: 'raw_nwp',
      rowClass: 'text-[#fbbf24]',
      headerBadge: null,
    },
    {
      name: t('ourModel'),
      key: 'model',
      rowClass: 'text-[#22c55e]',
      headerBadge: t('best'),
      highlight: true,
    },
  ]

  const val = (obj, field) => (obj ? fmtMetric(obj[field]) : '—')

  return (
    <div className="mx-auto max-w-[1100px] px-4 pb-8 pt-6">
      {!data && error ? (
        <div className="mb-4">
          <ServiceErrorBanner onRetry={load} />
        </div>
      ) : null}
      {data && usedFallback && error ? (
        <CachedDataNotice key={cacheNoticeKey} />
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <BarChart2 className="h-7 w-7 text-[#60a5fa]" aria-hidden />
          <div>
            <h1 className="text-xl font-medium tracking-tight text-main-text">
              {t('modelPerformance')}
            </h1>
            <p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted-text">
              {t('modelSubtitle')}
            </p>
          </div>
        </div>
        <button
          onClick={() => generateReport(data, null)}
          className="flex items-center gap-2 rounded-lg bg-[#22c55e]/10 border border-[#22c55e]/20 px-4 py-2 text-sm font-medium text-[#22c55e] transition-colors hover:bg-[#22c55e]/20"
        >
          <Download className="h-4 w-4" />
          {t('downloadReport') || 'Download Report'}
        </button>
      </div>

      {/* ── Tab switcher ─────────────────────────────────────────────────── */}
      <div className="mt-6 flex gap-1 rounded-xl border border-line bg-hover-bg p-1">
        <button
          type="button"
          onClick={() => setActiveTab('metrics')}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
            activeTab === 'metrics'
              ? 'bg-surface-bg text-main-text shadow-sm'
              : 'text-muted-text hover:text-main-text'
          }`}
        >
          <BarChart2 className="h-4 w-4" />
          {t('performanceMetrics') || 'Performance Metrics'}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('ledger')}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
            activeTab === 'ledger'
              ? 'bg-surface-bg text-main-text shadow-sm'
              : 'text-muted-text hover:text-main-text'
          }`}
        >
          <ClipboardList className="h-4 w-4" />
          {t('forecastLedger') || 'Forecast Ledger'}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('health')}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
            activeTab === 'health'
              ? 'bg-surface-bg text-main-text shadow-sm'
              : 'text-muted-text hover:text-main-text'
          }`}
        >
          <Activity className="h-4 w-4" />
          {t('modelHealth') || 'Model Health'}
        </button>
      </div>

      {activeTab === 'metrics' && (
        <>
          {imp ? (
            <div className="mt-8 grid grid-cols-1 gap-3 md:grid-cols-3">
              <StatCard
                title={t('solarImprovement')}
                value={imp.nmae_solar_pct != null ? `${imp.nmae_solar_pct}%` : '—'}
                subtitle={t('vsPersistence')}
                className="border-[#22c55e]/25 bg-[#22c55e]/8"
                valueClassName="text-[#22c55e]"
                icon={TrendingUp}
              />
              <StatCard
                title={t('windImprovement')}
                value={imp.nmae_wind_pct != null ? `${imp.nmae_wind_pct}%` : '—'}
                subtitle={t('vsPersistence')}
                className="border-[#22c55e]/25 bg-[#22c55e]/8"
                valueClassName="text-[#22c55e]"
                icon={TrendingUp}
              />
              <StatCard
                title={t('crpsImprovement')}
                value={imp.crps_pct != null ? `${imp.crps_pct}%` : '—'}
                subtitle={t('vsPersistence')}
                className="border-[#22c55e]/25 bg-[#22c55e]/8"
                valueClassName="text-[#22c55e]"
                icon={TrendingUp}
              />
            </div>
          ) : null}

          <div className="mt-8 overflow-x-auto rounded-xl border border-line bg-hover-bg">
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <thead>
                <tr className="bg-surface-bg text-left text-[11px] font-medium uppercase tracking-[0.06em] text-faint-text">
                  <th className="border-b border-line px-4 py-3">{t('model')}</th>
                  <th className="border-b border-line px-4 py-3">{t('nmaeSolar')}</th>
                  <th className="border-b border-line px-4 py-3">{t('nmaeWind')}</th>
                  <th className="border-b border-line px-4 py-3">CRPS</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const src = r.key === 'model' ? model : baselines?.[r.key]
                  const isBest = r.highlight
                  return (
                    <tr
                      key={r.key}
                      className={`border-b border-line transition-colors hover:bg-[#232636]/80 ${
                        isBest ? 'bg-[#22c55e]/6' : ''
                      }`}
                    >
                      <td
                        className={`px-4 py-3 font-medium ${
                          isBest ? 'text-[#22c55e]' : 'text-main-text'
                        }`}
                      >
                        <span className="inline-flex items-center gap-2">
                          {r.name}
                          {r.headerBadge ? (
                            <span className="rounded bg-[#22c55e]/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#22c55e]">
                              {r.headerBadge}
                            </span>
                          ) : null}
                        </span>
                      </td>
                      <td className={`px-4 py-3 tabular-nums ${r.rowClass}`}>
                        <div>{val(src, 'nmae_solar')}</div>
                        {isBest && imp ? (
                          <div
                            className="mt-1 text-[11px]"
                            style={{ color: improvementColor(imp.nmae_solar_pct) }}
                          >
                            ▼ {imp.nmae_solar_pct}% {t('vsPersistence')}
                          </div>
                        ) : null}
                      </td>
                      <td className={`px-4 py-3 tabular-nums ${r.rowClass}`}>
                        <div>{val(src, 'nmae_wind')}</div>
                        {isBest && imp ? (
                          <div
                            className="mt-1 text-[11px]"
                            style={{ color: improvementColor(imp.nmae_wind_pct) }}
                          >
                            ▼ {imp.nmae_wind_pct}% {t('vsPersistence')}
                          </div>
                        ) : null}
                      </td>
                      <td className={`px-4 py-3 tabular-nums ${r.rowClass}`}>
                        <div>{val(src, 'crps')}</div>
                        {isBest && imp ? (
                          <div
                            className="mt-1 text-[11px]"
                            style={{ color: improvementColor(imp.crps_pct) }}
                          >
                            ▼ {imp.crps_pct}% {t('vsPersistence')}
                          </div>
                        ) : null}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-6 flex gap-3 rounded-xl border border-line bg-hover-bg p-4 text-sm leading-relaxed text-muted-text">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-[#10b981]" aria-hidden />
            <p>{t('cqrCoverageDesc')}</p>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-line bg-surface-bg p-4">
              <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-faint-text">
                {t('persistence')}
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-muted-text">
                {t('persistenceDesc')}
              </p>
            </div>
            <div className="rounded-xl border border-line bg-surface-bg p-4">
              <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-faint-text">
                {t('climatological')}
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-muted-text">
                {t('climatologicalDesc')}
              </p>
            </div>
            <div className="rounded-xl border border-line bg-surface-bg p-4">
              <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-faint-text">
                {t('rawNwp')}
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-muted-text">
                {t('rawNwpDesc')}
              </p>
            </div>
          </div>
        </>
      )}

      {activeTab === 'ledger' && <ForecastLedger />}

      {activeTab === 'health' && <ModelHealthPanel />}

      <DataNote />
    </div>
  )
}
