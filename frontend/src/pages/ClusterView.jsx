import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fetchForecast, plantsInCluster, PLANTS } from '../api/client'
import ReconciliationToggle from '../components/ReconciliationToggle.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ServiceErrorBanner from '../components/ServiceErrorBanner.jsx'
import CachedDataNotice from '../components/CachedDataNotice.jsx'
import DataNote from '../components/DataNote.jsx'
import { Info } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext.jsx'

const BAR_COLORS = {
  PVG_S1: '#10b981',
  PVG_S2: '#60a5fa',
  MIX_S1: '#93c5fd',
  GAD_W1: '#34d399',
  GAD_W2: '#7c3aed',
  MIX_W1: '#c4b5fd',
}

const PLANT_NAMES = Object.fromEntries(PLANTS.map((p) => [p.id, p.name]))

function ClusterTooltip({ active, payload, label, t }) {
  if (!active || !payload?.length) return null
  const h = Number(label)
  const hh = String(h).padStart(2, '0')
  return (
    <div className="rounded-lg border border-line bg-hover-bg px-3 py-2 text-xs shadow-lg">
      <p className="mb-2 font-medium text-main-text">{hh}:00 {t('ist') || 'IST'}</p>
      <ul className="space-y-1">
        {payload.map((p) => (
          <li key={p.dataKey} className="flex justify-between gap-4 text-muted-text">
            <span style={{ color: p.color }}>{PLANT_NAMES[p.dataKey] || p.dataKey}</span>
            <span className="tabular-nums text-main-text">{Number(p.value).toFixed(1)} MW</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function ClusterView() {
  const { t } = useLanguage()
  const [selectedCluster, setSelectedCluster] = useState('A')
  const [forecasts, setForecasts] = useState({})
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)
  const [usedFallback, setUsedFallback] = useState(false)
  const [cacheNoticeKey, setCacheNoticeKey] = useState(0)
  const [mintEnabled, setMintEnabled] = useState(false)

  const plantIds = useMemo(
    () => plantsInCluster(selectedCluster).map((p) => p.id),
    [selectedCluster]
  )

  const loadCluster = useCallback(async () => {
    setLoading(true)
    setErr(null)
    setForecasts({})
    const ids = plantsInCluster(selectedCluster).map((p) => p.id)
    const results = await Promise.all(ids.map((id) => fetchForecast(id, 0, 'Normal Day')))
    const next = {}
    let fallback = false
    let firstErr = null
    let anyMissing = false
    results.forEach((r, i) => {
      next[ids[i]] = r.data
      if (r.usedFallback) fallback = true
      if (r.error) firstErr = r.error
      if (!r.data) anyMissing = true
    })
    setForecasts(next)
    setUsedFallback(fallback)
    setErr(firstErr)
    if (!anyMissing && fallback && firstErr) setCacheNoticeKey((k) => k + 1)
    setLoading(false)
  }, [selectedCluster])

  useEffect(() => {
    setMintEnabled(false)
  }, [selectedCluster])

  useEffect(() => {
    loadCluster()
  }, [loadCluster])

  const chartData = useMemo(() => {
    const hours = Array.from({ length: 24 }, (_, i) => i)
    return hours.map((h) => {
      const row = { hour: h }
      plantIds.forEach((pid) => {
        const f = forecasts[pid]
        row[pid] = f?.p50?.[h] ?? 0
      })
      return row
    })
  }, [forecasts, plantIds])

  // BUG 2 FIX: renamed from 't' to 'tab' to avoid shadowing the t() translation function
  const tabs = [
    { id: 'A', label: t('clusterA') },
    { id: 'B', label: t('clusterB') },
  ]

  return (
    <div className="mx-auto max-w-[1200px] px-4 pb-8 pt-6">
      {Object.values(forecasts).some((f) => f == null) && err ? (
        <div className="mb-4">
          <ServiceErrorBanner onRetry={loadCluster} />
        </div>
      ) : null}
      {usedFallback &&
      err &&
      plantIds.length > 0 &&
      plantIds.every((id) => forecasts[id] != null) &&
      !loading ? (
        <CachedDataNotice key={cacheNoticeKey} />
      ) : null}

      {/* BUG 2 FIX: map variable renamed from 't' to 'tab' throughout */}
      <div className="flex gap-2 border-b border-line">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setSelectedCluster(tab.id)}
            className={`border-b-2 px-4 py-3 text-sm font-medium transition-colors duration-200 ${
              selectedCluster === tab.id
                ? 'border-[#10b981] text-main-text'
                : 'border-transparent text-muted-text hover:text-main-text'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="relative mt-6">
        {loading ? (
          <div className="flex h-[280px] items-center justify-center rounded-xl border border-line bg-hover-bg">
            <LoadingSpinner />
          </div>
        ) : (
          <div className="h-[280px] w-full rounded-xl border border-line bg-hover-bg p-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
                <CartesianGrid stroke="var(--line)" strokeOpacity={0.5} vertical={false} />
                <XAxis
                  dataKey="hour"
                  tickFormatter={(v) => `${String(v).padStart(2, '0')}:00`}
                  stroke="var(--line)"
                  tick={{ fill: 'var(--muted-text)', fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--line)' }}
                />
                <YAxis
                  stroke="var(--line)"
                  tick={{ fill: 'var(--muted-text)', fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--line)' }}
                  width={44}
                />
                <Tooltip
                  content={<ClusterTooltip t={t} />}
                  cursor={{ fill: 'rgba(59,130,246,0.06)' }}
                />
                <Legend
                  wrapperStyle={{ fontSize: 12, color: 'var(--muted-text)' }}
                  formatter={(value) => PLANT_NAMES[value] || value}
                />
                {plantIds.map((pid) => (
                  <Bar
                    key={pid}
                    dataKey={pid}
                    stackId="cluster"
                    fill={BAR_COLORS[pid]}
                    isAnimationActive
                    animationDuration={800}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <section className="mt-10">
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-lg font-medium tracking-tight text-main-text">
            {t('hierarchicalConsistency')}
          </h2>
          <Info className="h-4 w-4 text-muted-text" aria-hidden />
        </div>
        <p className="mb-4 max-w-3xl text-sm leading-relaxed text-muted-text">
          {t('hierarchicalSubtitle')}
        </p>
        <ReconciliationToggle
          cluster={selectedCluster}
          mintEnabled={mintEnabled}
          onMintChange={setMintEnabled}
        />
      </section>

      <DataNote />
    </div>
  )
}
