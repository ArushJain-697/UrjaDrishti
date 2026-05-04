import { useEffect, useRef, useState } from 'react'
import { PLANTS, mockForecast } from '../api/client'

// India grid emission factor: tonnes CO2 per MWh
const EMISSION_FACTOR = 0.82
// Spinning reserve cost per MWh (INR)
const RESERVE_COST = 8000
// Model accuracy improvement over persistence baseline
const ACCURACY_IMPROVEMENT = 0.17

/** Compute carbon avoided and cost savings from all 6 plants' P50 forecasts */
function computeTotals() {
  let totalMwh = 0
  for (const plant of PLANTS) {
    const { p50 } = mockForecast(plant.id, 'Normal Day')
    totalMwh += p50.reduce((s, v) => s + v, 0) // sum of 24 hourly MW values = MWh
  }
  const carbonT = Math.round(totalMwh * EMISSION_FACTOR)
  const savingsLakh = (totalMwh * ACCURACY_IMPROVEMENT * RESERVE_COST) / 100_000
  return { carbonT, savingsLakh }
}

/** Smooth ease-out count-up animation */
function useCountUp(target, duration = 1800) {
  const [value, setValue] = useState(0)
  const rafRef = useRef(null)
  const startRef = useRef(null)

  useEffect(() => {
    if (!target) return
    startRef.current = null
    const step = (ts) => {
      if (!startRef.current) startRef.current = ts
      const progress = Math.min((ts - startRef.current) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3) // cubic ease-out
      setValue(target * eased)
      if (progress < 1) rafRef.current = requestAnimationFrame(step)
    }
    rafRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, duration])

  return value
}

export default function ImpactCounters() {
  const [totals] = useState(() => computeTotals())

  const carbon = useCountUp(totals.carbonT)
  const savings = useCountUp(totals.savingsLakh)

  return (
    <div className="hidden items-center gap-1 sm:flex">
      {/* Carbon avoided */}
      <div
        className="flex flex-col items-center rounded-lg border border-[#22c55e]/25 bg-[#22c55e]/8 px-3 py-1.5 transition-all duration-300 hover:border-[#22c55e]/50 hover:bg-[#22c55e]/12"
        title="CO₂ avoided today vs equivalent fossil generation"
      >
        <span className="text-[13px] font-semibold tabular-nums leading-tight text-[#22c55e]">
          🌱 {Math.round(carbon).toLocaleString('en-IN')} t
        </span>
        <span className="text-[10px] font-medium uppercase tracking-wide text-[#22c55e]/60">
          CO₂ avoided
        </span>
      </div>

      {/* Cost savings */}
      <div
        className="flex flex-col items-center rounded-lg border border-[#22c55e]/25 bg-[#22c55e]/8 px-3 py-1.5 transition-all duration-300 hover:border-[#22c55e]/50 hover:bg-[#22c55e]/12"
        title="Estimated spinning reserve savings from improved forecast accuracy"
      >
        <span className="text-[13px] font-semibold tabular-nums leading-tight text-[#22c55e]">
          ₹ {savings.toFixed(1)}L
        </span>
        <span className="text-[10px] font-medium uppercase tracking-wide text-[#22c55e]/60">
          saved today
        </span>
      </div>
    </div>
  )
}
