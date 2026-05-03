import { useCallback, useEffect, useState } from 'react'
import { Check, Equal, X as XIcon } from 'lucide-react'
import { fetchReconciled, formatMw } from '../api/client'
import LoadingSpinner from './LoadingSpinner'
import ServiceErrorBanner from './ServiceErrorBanner'

export default function ReconciliationToggle({ cluster, mintEnabled, onMintChange }) {
  const clusterKey = cluster === 'A' ? 'cluster_a' : 'cluster_b'
  const [payload, setPayload] = useState(null)
  const [loading, setLoading] = useState(true)
  const [usedMock, setUsedMock] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    const res = await fetchReconciled()
    setPayload(res.data)
    setUsedMock(res.usedMock)
    setError(res.error)
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const block = payload?.[clusterKey]
  const view = mintEnabled ? block?.post_mint : block?.pre_mint

  return (
    <div className="rounded-xl border border-[#2a2d3e] bg-[#1e2130] p-4">
      {usedMock && error ? (
        <div className="mb-4">
          <ServiceErrorBanner onRetry={load} />
        </div>
      ) : null}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[#e8eaf0]">MinT reconciliation view</p>
          <p className="mt-0.5 text-[12px] text-[#8b8fa8]">
            Toggle OFF for pre-MinT inconsistency, ON for post-MinT reconciled totals
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={mintEnabled}
          onClick={() => onMintChange(!mintEnabled)}
          className={`relative h-9 w-16 shrink-0 rounded-full transition-colors duration-200 ${
            mintEnabled ? 'bg-[#22c55e]' : 'bg-[#5a5d72]'
          }`}
        >
          <span
            className={`absolute top-1 left-1 flex h-7 w-7 items-center justify-center rounded-full bg-white shadow transition-transform duration-200 ease-out ${
              mintEnabled ? 'translate-x-7' : 'translate-x-0'
            }`}
          >
            <span className="text-[10px] font-bold text-[#1a1d27]">{mintEnabled ? 'ON' : 'OFF'}</span>
          </span>
        </button>
      </div>

      <div className="relative mt-6 min-h-[140px]">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : (
          <div
            key={mintEnabled ? 'mint-on' : 'mint-off'}
            className="transition-opacity duration-300 motion-safe:animate-[fadeRecon_280ms_ease-out]"
          >
            {!view ? (
              <p className="text-sm text-[#8b8fa8]">No reconciliation data</p>
            ) : (
              <>
                <div className="grid grid-cols-1 items-center gap-4 md:grid-cols-[1fr_auto_1fr]">
                  <div className="rounded-lg border border-[#2a2d3e] bg-[#1a1d27] p-4 text-center transition-colors duration-300">
                    <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#5a5d72]">
                      Plant Sum
                    </p>
                    <p
                      className={`mt-2 text-xl font-medium tabular-nums ${
                        mintEnabled ? 'text-[#22c55e]' : 'text-[#ef4444]'
                      }`}
                    >
                      {formatMw(view.plant_sum)} MW
                    </p>
                  </div>
                  <div className="flex justify-center">
                    {mintEnabled ? (
                      <Equal className="h-10 w-10 text-[#22c55e]" strokeWidth={2.5} aria-hidden />
                    ) : (
                      <span className="text-3xl font-light text-[#ef4444]" aria-hidden>
                        ≠
                      </span>
                    )}
                  </div>
                  <div className="rounded-lg border border-[#2a2d3e] bg-[#1a1d27] p-4 text-center transition-colors duration-300">
                    <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#5a5d72]">
                      Cluster Forecast
                    </p>
                    <p
                      className={`mt-2 text-xl font-medium tabular-nums ${
                        mintEnabled ? 'text-[#22c55e]' : 'text-[#ef4444]'
                      }`}
                    >
                      {formatMw(view.cluster_forecast)} MW
                    </p>
                  </div>
                </div>
                <div className="mt-4 flex justify-center transition-opacity duration-300">
                  {mintEnabled ? (
                    <span className="inline-flex items-center gap-2 rounded-full border border-[#22c55e]/40 bg-[#22c55e]/10 px-3 py-1.5 text-[12px] font-medium text-[#22c55e]">
                      <Check className="h-4 w-4" aria-hidden />
                      RECONCILED ✓ — MinT reconciliation applied, mathematically guaranteed
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2 rounded-full border border-[#ef4444]/40 bg-[#ef4444]/10 px-3 py-1.5 text-[12px] font-medium text-[#ef4444]">
                      <XIcon className="h-4 w-4" aria-hidden />
                      INCONSISTENT — plant and cluster dashboards contradict each other
                    </span>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
