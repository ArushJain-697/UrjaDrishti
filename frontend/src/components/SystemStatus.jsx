import { useEffect, useState } from 'react'
import { Lock } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext.jsx'

function formatIST(d) {
  return d.toLocaleTimeString('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export default function SystemStatus() {
  const [now, setNow] = useState(() => new Date())
  const { t } = useLanguage()

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="flex flex-wrap items-center justify-end gap-2 sm:gap-3 text-[11px]">
      <div className="flex items-center gap-2">
        <span
          className="inline-block h-2 w-2 rounded-full bg-[#22c55e] animate-pulse-dot"
          aria-hidden
        />
        <span className="text-[11px] font-semibold uppercase tracking-wide text-[#22c55e]">
          {t('live')}
        </span>
      </div>
      <span className="hidden h-4 w-px bg-[#2a2d3e] sm:inline" aria-hidden />
      <span className="inline-flex items-baseline gap-1.5">
        <span className="font-mono tabular-nums text-[#e8eaf0]">{formatIST(now)}</span>
        <span className="text-[10px] font-medium uppercase tracking-wide text-[#5a5d72]">
          IST
        </span>
      </span>
      <span className="hidden h-4 w-px bg-[#2a2d3e] md:inline" aria-hidden />
      <span className="hidden text-[#8b8fa8] md:inline">KREDL / KSPDCL</span>
      <span className="flex items-center gap-1 text-[#5a5d72]">
        <Lock className="h-3.5 w-3.5" aria-hidden />
        <span>{t('onPremise')}</span>
      </span>
    </div>
  )
}
