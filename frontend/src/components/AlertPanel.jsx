import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, Bell, CheckCircle, Info } from 'lucide-react'
import { fetchAlerts } from '../api/client'
import LoadingSpinner from './LoadingSpinner'
import { useLanguage } from '../context/LanguageContext.jsx'

const border = {
  warning: 'border-l-[#f59e0b]',
  success: 'border-l-[#22c55e]',
  info: 'border-l-[#3b82f6]',
}

const Icon = {
  warning: AlertTriangle,
  success: CheckCircle,
  info: Info,
}

const ALERT_TEXT_KEYS = {
  warning: 'holdReserve',
  success: 'safeToSchedule',
  info: 'highUncertainty',
}

export default function AlertPanel({ plantId, p50, hours }) {
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
    setAlerts(res.data?.alerts ?? [])
    setError(res.error)
    setLoading(false)
  }, [plantId, p50, hours])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="flex h-full min-h-[320px] flex-col rounded-xl border border-[#2a2d3e] bg-[#1e2130]">
      <div className="flex items-center gap-2 border-b border-[#2a2d3e] px-4 py-3">
        <Bell className="h-4 w-4 text-[#60a5fa]" aria-hidden />
        <h2 className="text-sm font-medium tracking-tight text-[#e8eaf0]">{t('forecastAlerts')}</h2>
      </div>

      {error && !alerts.length && !loading ? (
        <div className="px-4 pt-3">
          <p className="rounded-lg border border-[#ef4444]/50 bg-[#1e2130] px-3 py-2 text-[13px] text-[#8b8fa8]">
            Unable to load alerts.{' '}
            <button
              type="button"
              onClick={load}
              className="text-[#60a5fa] underline hover:no-underline"
            >
              Retry
            </button>
          </p>
        </div>
      ) : null}

      <div className="relative flex-1 p-4">
        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <LoadingSpinner />
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 py-12 text-center">
            <CheckCircle className="h-10 w-10 text-[#22c55e]" aria-hidden />
            <p className="max-w-xs text-sm leading-relaxed text-[#8b8fa8]">
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
                  className={`rounded-lg border border-[#2a2d3e] border-l-[3px] bg-[#232636] ${border[a.type] || border.info} transition-colors hover:bg-[#262a3d]`}
                >
                  <div className="flex gap-3 p-3">
                    <I
                      className={`mt-0.5 h-4 w-4 shrink-0 ${
                        a.type === 'warning'
                          ? 'text-[#f59e0b]'
                          : a.type === 'success'
                            ? 'text-[#22c55e]'
                            : 'text-[#3b82f6]'
                      }`}
                      aria-hidden
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#5a5d72]">
                        {String(a.hour).padStart(2, '0')}:00
                      </p>
                      <p className="mt-1 text-[13px] leading-relaxed text-[#e8eaf0]">
                        {t(ALERT_TEXT_KEYS[a.type] || 'highUncertainty')}
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
