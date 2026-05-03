import { RefreshCw } from 'lucide-react'

export default function ServiceErrorBanner({ onRetry }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-[#ef4444]/50 bg-[#1e2130] px-3 py-2 text-sm text-[#e8eaf0]">
      <p className="text-[13px] leading-snug text-[#8b8fa8]">
        Unable to reach forecast service — showing cached data
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex shrink-0 items-center gap-1 rounded-md border border-[#2a2d3e] bg-[#1a1d27] px-2 py-1 text-[12px] text-[#e8eaf0] transition hover:border-[#3b82f6]/40"
      >
        <RefreshCw className="h-3.5 w-3.5" aria-hidden />
        Retry
      </button>
    </div>
  )
}
