import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, Bell, CheckCircle, Info, Wrench } from 'lucide-react'
import { fetchAlerts } from '../api/client'
import LoadingSpinner from './LoadingSpinner'
import { useLanguage } from '../context/LanguageContext.jsx'

const border = {
  warning: 'border-l-[#f59e0b]',
  success: 'border-l-[#22c55e]',
  info: 'border-l-[#10b981]',
  hardware_anomaly: 'border-l-[#f97316]',
}

const Icon = {
  warning: AlertTriangle,
  success: CheckCircle,
  info: Info,
  hardware_anomaly: Wrench,
}

const iconColor = {
  warning: 'text-[#f59e0b]',
  success: 'text-[#22c55e]',
  info: 'text-[#10b981]',
  hardware_anomaly: 'text-[#f97316]',
}

export default function AlertPanel({ plantId, p50, hours, onAlertsLoaded }) {
  const { t } = useLanguage()
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    if (!plantId || !p50?.length || !hours?.length) {
      setAlerts([])
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    const res = await fetchAlerts(plantId, p50, hours)
    const fetchedAlerts = res.data?.alerts ?? []
    setAlerts(fetchedAlerts)
    if (onAlertsLoaded) onAlertsLoaded(fetchedAlerts)
    setError(res.error)
    setLoading(false)
  }, [plantId, p50, hours, onAlertsLoaded])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="flex flex-col rounded-xl border border-line bg-hover-bg" style={{ maxHeight: 480 }}>
      <div className="flex items-center gap-2 border-b border-line px-4 py-3">
        <Bell className="h-4 w-4 text-emerald-500" aria-hidden />
        <h2 className="text-sm font-medium tracking-tight text-main-text">{t('forecastAlerts')}</h2>
      </div>

      {error && !alerts.length && !loading ? (
        <div className="px-4 pt-3">
          <p className="rounded-lg border border-[#ef4444]/50 bg-hover-bg px-3 py-2 text-[13px] text-muted-text">
            Unable to load alerts.{' '}
            <button
              type="button"
              onClick={load}
              className="text-emerald-500 underline hover:no-underline"
            >
              Retry
            </button>
          </p>
        </div>
      ) : null}

      <div className="relative flex-1 overflow-y-auto p-4" style={{ minHeight: 0 }}>
        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <LoadingSpinner />
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 py-12 text-center">
            <CheckCircle className="h-10 w-10 text-[#22c55e]" aria-hidden />
            <p className="max-w-xs text-sm leading-relaxed text-muted-text">
              {t('noAlerts')}
            </p>
          </div>
        ) : (
          <ul className="flex flex-col gap-3">
            {alerts.map((a) => {
              const I = Icon[a.type] || Info
              return (
                <li
                  key={`${a.hour}-${a.type}`}
                  className={`rounded-lg border border-line border-l-[3px] bg-surface-bg ${border[a.type] || border.info} transition-colors hover:bg-hover-bg`}
                >
                  <div className="flex gap-3 p-3">
                    <I
                      className={`mt-0.5 h-4 w-4 shrink-0 ${iconColor[a.type] ?? iconColor.info}`}
                      aria-hidden
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-faint-text">
                        {String(a.hour).padStart(2, '0')}:00
                      </p>
                      <p className="mt-1 text-[13px] leading-relaxed text-main-text">
                        {(() => {
                          const templates = t('alertTemplates');
                          if (templates && a.template && templates[a.template]) {
                            const impactMatch = a.message.match(/~([\d\.]+)%/);
                            const impact = impactMatch ? impactMatch[1] : '';
                            return templates[a.template]
                              .replace('{hour}', String(a.hour).padStart(2, '0'))
                              .replace('{impact}', impact);
                          }
                          return a.message;
                        })()}
                      </p>
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
