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
      <span className="inline-flex items-baseline gap-1.5">
        <span className="font-mono tabular-nums text-main-text">{formatIST(now)}</span>
        <span className="text-[10px] font-medium uppercase tracking-wide text-faint-text">
          IST
        </span>
      </span>
    </div>
  )
}
