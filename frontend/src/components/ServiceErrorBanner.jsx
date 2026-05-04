import { RefreshCw } from 'lucide-react'

export default function ServiceErrorBanner({ onRetry }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-[#ef4444]/50 bg-hover-bg px-3 py-2 text-sm text-main-text">
      <p className="text-[13px] leading-snug text-muted-text">
        Unable to reach forecast service — showing cached data
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex shrink-0 items-center gap-1 rounded-md border border-line bg-surface-bg px-2 py-1 text-[12px] text-main-text transition hover:border-[#10b981] transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_10px_rgba(16,185,129,0.2)]/40"
      >
        <RefreshCw className="h-3.5 w-3.5" aria-hidden />
        Retry
      </button>
    </div>
  )
}
