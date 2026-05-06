import { useMemo } from 'react'
import { useLanguage } from '../context/LanguageContext.jsx'

/**
 * Compute a 1–10 confidence score from P10/P90 interval width and plant capacity.
 * Narrower intervals → higher score → more confident forecast.
 */
function computeConfidence(p10, p90, capacityMw) {
  if (!p10?.length || !p90?.length || !capacityMw) return null
  const avgWidth = p90.reduce((sum, v, i) => sum + (v - p10[i]), 0) / p90.length
  const score = Math.max(1, Math.min(10, 10 - (avgWidth / capacityMw) * 10))
  return Math.round(score * 10) / 10
}

function scoreColor(score) {
  if (score >= 7) return { hex: '#22c55e', ring: 'rgba(34,197,94,0.18)', glow: 'rgba(34,197,94,0.35)' }
  if (score >= 4) return { hex: '#f59e0b', ring: 'rgba(245,158,11,0.18)', glow: 'rgba(245,158,11,0.35)' }
  return { hex: '#ef4444', ring: 'rgba(239,68,68,0.18)', glow: 'rgba(239,68,68,0.35)' }
}

function segmentColor(segIndex, score) {
  // segIndex is 0-based (segment 0 = score 1, segment 9 = score 10)
  const segScore = segIndex + 1
  const filled = segScore <= Math.round(score)
  if (!filled) return 'var(--hover-bg, #1e2130)'
  if (segScore <= 3) return '#ef4444'
  if (segScore <= 6) return '#f59e0b'
  return '#22c55e'
}

export default function ConfidenceScore({ p10, p90, capacityMw }) {
  const { t } = useLanguage()

  const score = useMemo(
    () => computeConfidence(p10, p90, capacityMw),
    [p10, p90, capacityMw]
  )

  if (score === null) return null

  const { hex, ring, glow } = scoreColor(score)

  const label =
    score >= 7
      ? t('safeToSchedule')
      : score >= 4
      ? t('holdReserve')
      : t('highUncertainty')

  const icon =
    score >= 7 ? '✓' : score >= 4 ? '⚡' : '⚠'

  return (
    <div
      className="mt-6 w-full overflow-hidden rounded-xl border transition-all duration-500"
      style={{
        borderColor: hex,
        background: ring,
        boxShadow: `0 0 24px ${glow}`,
      }}
    >
      <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:gap-8">

        {/* ── Left: big score number ─────────────────────────── */}
        <div className="flex min-w-0 shrink-0 flex-col gap-1">
          <p
            className="text-[11px] font-semibold uppercase tracking-[0.1em]"
            style={{ color: hex, opacity: 0.8 }}
          >
            {t('confidenceScore')}
          </p>

          <div className="flex items-end gap-3">
            <span
              className="font-bold leading-none tabular-nums transition-all duration-500"
              style={{ fontSize: 64, color: hex, lineHeight: 1 }}
            >
              {score.toFixed(1)}
            </span>
            <span
              className="mb-1 text-[22px] font-medium"
              style={{ color: hex, opacity: 0.7 }}
            >
              / 10
            </span>
          </div>

          <div
            className="mt-1 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-semibold"
            style={{ background: ring, color: hex }}
          >
            <span>{icon}</span>
            <span>{label}</span>
          </div>
        </div>

        {/* ── Right: 10-segment gauge ───────────────────────── */}
        <div className="flex flex-1 flex-col gap-3">
          {/* Gauge bar */}
          <div className="flex items-center gap-1.5">
            {Array.from({ length: 10 }, (_, i) => {
              const filled = i + 1 <= Math.round(score)
              const color = segmentColor(i, score)
              return (
                <div
                  key={i}
                  className="flex-1 rounded-sm transition-all duration-500"
                  style={{
                    height: 14,
                    background: color,
                    opacity: filled ? 1 : 0.15,
                    boxShadow: filled ? `0 0 6px ${color}99` : 'none',
                  }}
                />
              )
            })}
          </div>

          {/* Scale labels */}
          <div className="flex justify-between text-[10px] font-medium tracking-wide" style={{ color: 'var(--faint-text, #5a5d72)' }}>
            <span style={{ color: '#ef4444' }}>1 {t('low')}</span>
            <span style={{ color: '#f59e0b' }}>5 {t('medium')}</span>
            <span style={{ color: '#22c55e' }}>10 {t('high')}</span>
          </div>
 
          {/* Legend dots */}
          <div className="mt-1 flex flex-wrap gap-4 text-[11px]" style={{ color: 'var(--muted-text, #8b8fa8)' }}>
            {[
              { color: '#22c55e', label: `7-10 — ${t('scheduleTightly')}` },
              { color: '#f59e0b', label: `4-6 — ${t('holdReserveLegend')}` },
              { color: '#ef4444', label: `1-3 — ${t('waitForUpdateLegend')}` },
            ].map(({ color, label: l }) => (
              <span key={color} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ background: color }}
                />
                {l}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
