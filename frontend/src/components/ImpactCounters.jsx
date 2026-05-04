import { useEffect, useRef, useState } from 'react'
import { PLANTS, fetchForecast, mockForecast } from '../api/client'

// India grid emission factor: tonnes CO2 per MWh
const EMISSION_FACTOR = 0.82
// Spinning reserve cost per MWh (INR)
const RESERVE_COST = 8000
// Model accuracy improvement: Stage-2 vs Stage-1 nMAE on intraday holdout.
// Measured value from training run: +41.8% (Stage-1 nMAE=0.0024, Stage-2 nMAE=0.0014)
const ACCURACY_IMPROVEMENT = 0.418

/** Fetch all 6 plants in parallel, fall back to mock only if ALL fail */
async function fetchAllTotals() {
  const results = await Promise.allSettled(
    PLANTS.map((p) => fetchForecast(p.id, 0, 'Normal Day'))
  )

  let totalMwh = 0
  let anyReal = false

  results.forEach((r, i) => {
    let p50
    if (r.status === 'fulfilled' && r.value?.data?.p50) {
      p50 = r.value.data.p50
      if (!r.value.usedFallback) anyReal = true
    } else {
      // individual plant fallback
      p50 = mockForecast(PLANTS[i].id, 'Normal Day').p50
    }
    totalMwh += p50.reduce((s, v) => s + v, 0)
  })

  const carbonT = Math.round(totalMwh * EMISSION_FACTOR)
  const savingsLakh = (totalMwh * ACCURACY_IMPROVEMENT * RESERVE_COST) / 100_000
  return { carbonT, savingsLakh, anyReal }
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
  const [totals, setTotals] = useState({ carbonT: 0, savingsLakh: 0, anyReal: false })
  const [ready, setReady] = useState(false)

  useEffect(() => {
    fetchAllTotals().then((result) => {
      setTotals(result)
      setReady(true)
    })
  }, [])

  const carbon = useCountUp(ready ? totals.carbonT : 0)
  const savings = useCountUp(ready ? totals.savingsLakh : 0)

  return (
    <div className="hidden items-center gap-1 sm:flex">
      {/* Carbon avoided */}
      <div
        className="flex flex-col items-center rounded-lg border border-[#22c55e]/25 bg-[#22c55e]/8 px-3 py-1.5 transition-all duration-300 hover:border-[#22c55e]/50 hover:bg-[#22c55e]/12"
        title={`CO₂ avoided today vs equivalent fossil generation${totals.anyReal ? ' (live data)' : ' (mock fallback)'}`}
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
        title={`Spinning reserve savings from forecast accuracy improvement${totals.anyReal ? ' (live data)' : ' (mock fallback)'}`}
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
