import { formatMw } from '../api/client'
import { useLanguage } from '../context/LanguageContext.jsx'

function bandColor(avgWidth) {
  if (avgWidth < 20) return 'text-[#22c55e]'
  if (avgWidth <= 35) return 'text-[#f59e0b]'
  return 'text-[#ef4444]'
}

function avgBand(p10, p90, fromH, toH) {
  let sum = 0
  let n = 0
  for (let i = 0; i < p10.length; i++) {
    const h = i
    if (h >= fromH && h <= toH) {
      sum += p90[i] - p10[i]
      n += 1
    }
  }
  if (n === 0) return 0
  return sum / n
}

export default function IntervalStats({ p10, p90 }) {
  const { t } = useLanguage()
  const morning = avgBand(p10, p90, 6, 12)
  const afternoon = avgBand(p10, p90, 13, 18)

  const cards = [
    { label: t('morningConfidence'), value: morning },
    { label: t('afternoonConfidence'), value: afternoon },
  ]

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {cards.map((c) => (
        <div
          key={c.label}
          className="rounded-xl border border-[#2a2d3e] bg-[#1e2130] p-4"
        >
          <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#5a5d72]">
            {c.label}
          </p>
          <p className={`mt-2 text-2xl font-medium tracking-tight ${bandColor(c.value)}`}>
            {formatMw(c.value)} MW
          </p>
          <p className="mt-1 text-[12px] text-[#8b8fa8]">{t('avgConfidenceBand')}</p>
        </div>
      ))}
    </div>
  )
}
