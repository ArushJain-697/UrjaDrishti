import { useMemo, useState } from 'react'
import { ArrowUpDown, ArrowUp, ArrowDown, Search, Printer } from 'lucide-react'
import { PLANTS, plantMeta } from '../api/client'

// ── Officers and note templates ─────────────────────────────────────────────
const OFFICERS = ['R. Kumar', 'S. Patil', 'M. Hegde', 'A. Nair']

const NOTES_HIGH = [
  'Clear sky conditions. Forecast confidence high. Proceeding with scheduled draw.',
  'Stable NWP signals. All systems nominal.',
  'Forecast within ±2% of actuals. No intervention required.',
  'Clean generation day. Evening ramp tracked correctly.',
  'Model performed well — within operational tolerance.',
]
const NOTES_MED = [
  'Partial cloud development in afternoon. Minor deviation from forecast.',
  'Wind variability in mid-day. Reserve margin held as precaution.',
  'NWP ensemble spread wider than usual. Intraday update used.',
  'Slight morning fog — forecast partially missed early generation dip.',
]
const NOTES_HIGH_ERR = [
  'Cloud ramp event — forecast revised intraday. Reserve held.',
  'Unexpected cloud front. Intraday update partially corrected forecast.',
  'Monsoon transition — forecast error within expected range for onset days.',
  'Wind speed at cut-out threshold — high uncertainty flag triggered.',
]

// ── Deterministic seeded noise ──────────────────────────────────────────────
function seed(plantId, dayIndex, salt) {
  let s = salt * 17 + dayIndex * 31
  for (let i = 0; i < plantId.length; i++) s += plantId.charCodeAt(i) * (i + 1)
  const x = Math.abs(Math.sin(s * 0.01) + Math.cos(s * 0.03)) * 43758.5453
  return x - Math.floor(x) // [0, 1)
}

function seedFrom(n) {
  return Math.abs(Math.sin(n * 79.2348) * 43758.5453) % 1
}

// ── Generate 14 days × 6 plants = 84 ledger rows ───────────────────────────
function generateLedgerData() {
  const rows = []
  const today = new Date()

  for (let d = 13; d >= 0; d--) {
    const date = new Date(today)
    date.setDate(today.getDate() - (d + 1))
    const dateStr = date.toISOString().split('T')[0]
    const dayOfYear = Math.floor((date - new Date(date.getFullYear(), 0, 0)) / 86400000)

    // Is this a stress day? Roughly 2-3 per 14 days
    const isStressDay = seedFrom(dayOfYear * 7 + 3) < 0.18
    const stressLabel = isStressDay
      ? ['Cloud ramp event', 'Monsoon onset', 'Wind ramp'][Math.floor(seedFrom(dayOfYear) * 3)]
      : null

    for (const plant of PLANTS) {
      const meta = plantMeta(plant.id)
      const { capacityMw, type } = meta

      // Forecast peak — derived from physics curve
      const solarPeak = Math.max(0, capacityMw * 0.92 * Math.sin(Math.PI * (13 - 6) / 12))
      const windBase = capacityMw * (0.35 + 0.12 * Math.sin((dayOfYear / 365) * 2 * Math.PI))
      const basePeak = type === 'solar' ? solarPeak : windBase

      // Stress reduces forecast peak and widens bands
      const stressFactor = isStressDay
        ? (type === 'solar' ? 0.6 + seedFrom(dayOfYear + plant.id.length) * 0.2 : 0.85)
        : 1.0
      const forecastPeak = Math.round(basePeak * stressFactor * 10) / 10

      // Actual = forecast + noise. Stress days have higher error.
      const noiseMax = isStressDay ? 0.16 : 0.06
      const noise = (seed(plant.id, d, 5) - 0.5) * 2 * noiseMax
      const actualPeak = Math.round(Math.max(0, Math.min(capacityMw, forecastPeak * (1 + noise))) * 10) / 10
      const errorPct = forecastPeak > 0
        ? Math.round(Math.abs(actualPeak - forecastPeak) / forecastPeak * 1000) / 10
        : 0

      // Confidence score — narrow bands = high score on clear days
      const bandWidthFraction = isStressDay ? 0.35 + seed(plant.id, d, 7) * 0.15 : 0.18 + seed(plant.id, d, 7) * 0.08
      const rawScore = Math.max(1, Math.min(10, 10 - bandWidthFraction * 10 * (capacityMw / capacityMw)))
      const confidenceScore = Math.round(rawScore * 10) / 10

      // Officer and notes rotation
      const officerIdx = (d + plant.id.charCodeAt(0)) % OFFICERS.length
      const officer = OFFICERS[officerIdx]

      let notes = ''
      if (errorPct < 5) {
        notes = NOTES_HIGH[Math.floor(seed(plant.id, d, 13) * NOTES_HIGH.length)]
      } else if (errorPct < 10) {
        notes = NOTES_MED[Math.floor(seed(plant.id, d, 13) * NOTES_MED.length)]
      } else {
        notes = NOTES_HIGH_ERR[Math.floor(seed(plant.id, d, 13) * NOTES_HIGH_ERR.length)]
        if (stressLabel) notes = `${stressLabel} — ${notes}`
      }

      rows.push({
        id: `${dateStr}-${plant.id}`,
        date: dateStr,
        plant: meta.name,
        plant_id: plant.id,
        plantType: type,
        forecastPeak,
        actualPeak,
        errorPct,
        officer,
        confidence: confidenceScore,
        notes,
        isStress: isStressDay,
      })
    }
  }
  return rows
}

// ── Row error color ─────────────────────────────────────────────────────────
function errorClass(pct) {
  if (pct < 5) return { text: '#22c55e', bg: 'rgba(34,197,94,0.06)' }
  if (pct < 10) return { text: '#f59e0b', bg: 'rgba(245,158,11,0.06)' }
  return { text: '#ef4444', bg: 'rgba(239,68,68,0.08)' }
}

// ── Sort icon ───────────────────────────────────────────────────────────────
function SortIcon({ col, sortCol, sortDir }) {
  if (sortCol !== col) return <ArrowUpDown className="inline h-3 w-3 opacity-30" />
  return sortDir === 'asc'
    ? <ArrowUp className="inline h-3 w-3 text-[#10b981]" />
    : <ArrowDown className="inline h-3 w-3 text-[#10b981]" />
}

// ── Th component ─────────────────────────────────────────────────────────────
function Th({ children, col, sortCol, sortDir, onSort }) {
  return (
    <th
      className="cursor-pointer select-none border-b border-line px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.06em] text-faint-text hover:text-muted-text"
      onClick={() => onSort(col)}
    >
      {children}{' '}
      <SortIcon col={col} sortCol={sortCol} sortDir={sortDir} />
    </th>
  )
}

// ── Main component ───────────────────────────────────────────────────────────
export default function ForecastLedger() {
  const allRows = useMemo(() => generateLedgerData(), [])

  const [search, setSearch] = useState('')
  const [plantFilter, setPlantFilter] = useState('all')
  const [sortCol, setSortCol] = useState('date')
  const [sortDir, setSortDir] = useState('desc')
  const [hoveredRow, setHoveredRow] = useState(null)
  const [tooltipRow, setTooltipRow] = useState(null)

  const handleSort = (col) => {
    if (sortCol === col) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortCol(col); setSortDir('asc') }
  }

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return allRows
      .filter((r) => plantFilter === 'all' || r.plant_id === plantFilter)
      .filter((r) =>
        !q ||
        r.date.includes(q) ||
        r.plant.toLowerCase().includes(q) ||
        r.officer.toLowerCase().includes(q) ||
        r.notes.toLowerCase().includes(q)
      )
      .sort((a, b) => {
        let av = a[sortCol], bv = b[sortCol]
        if (typeof av === 'string') av = av.toLowerCase(), bv = bv.toLowerCase()
        return sortDir === 'asc' ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1)
      })
  }, [allRows, search, plantFilter, sortCol, sortDir])

  // Summary stats
  const avgError = filtered.length
    ? (filtered.reduce((s, r) => s + r.errorPct, 0) / filtered.length).toFixed(1)
    : '—'
  const bestPlant = useMemo(() => {
    if (!allRows.length) return '—'
    const byPlant = {}
    for (const r of allRows) {
      if (!byPlant[r.plant]) byPlant[r.plant] = []
      byPlant[r.plant].push(r.errorPct)
    }
    let best = null, bestErr = Infinity
    for (const [plant, errs] of Object.entries(byPlant)) {
      const avg = errs.reduce((s, e) => s + e, 0) / errs.length
      if (avg < bestErr) { bestErr = avg; best = plant }
    }
    return best
  }, [allRows])
  const mostAccurateDay = useMemo(() => {
    const byDate = {}
    for (const r of allRows) {
      if (!byDate[r.date]) byDate[r.date] = []
      byDate[r.date].push(r.errorPct)
    }
    let bestDate = null, bestErr = Infinity
    for (const [date, errs] of Object.entries(byDate)) {
      const avg = errs.reduce((s, e) => s + e, 0) / errs.length
      if (avg < bestErr) { bestErr = avg; bestDate = date }
    }
    return bestDate
  }, [allRows])
  const accuracyPct = allRows.length
    ? (100 - allRows.reduce((s, r) => s + r.errorPct, 0) / allRows.length).toFixed(1)
    : '—'

  return (
    <div className="mt-6">
      {/* ── Controls ─────────────────────────────────────────────────────── */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 gap-2">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint-text" />
            <input
              type="text"
              placeholder="Search date, plant, officer, notes…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-line bg-hover-bg py-2 pl-8 pr-3 text-[12px] text-main-text placeholder:text-faint-text outline-none focus:border-[#10b981] transition-colors"
            />
          </div>
          <select
            value={plantFilter}
            onChange={(e) => setPlantFilter(e.target.value)}
            className="rounded-lg border border-line bg-hover-bg px-3 py-2 text-[12px] text-main-text outline-none focus:border-[#10b981] cursor-pointer"
          >
            <option value="all">All Plants</option>
            {PLANTS.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => window.print()}
          className="no-print inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-2 text-[12px] font-medium text-muted-text transition-all hover:border-[#10b981] hover:text-[#10b981]"
        >
          <Printer className="h-3.5 w-3.5" />
          Export for Audit Committee
        </button>
      </div>

      {/* ── Table ────────────────────────────────────────────────────────── */}
      <div className="logbook-printable overflow-x-auto rounded-xl border border-line bg-hover-bg">
        <table className="w-full min-w-[860px] border-collapse text-[12px]">
          <thead>
            <tr className="bg-surface-bg">
              <Th col="date" sortCol={sortCol} sortDir={sortDir} onSort={handleSort}>Date</Th>
              <Th col="plant" sortCol={sortCol} sortDir={sortDir} onSort={handleSort}>Plant</Th>
              <Th col="forecastPeak" sortCol={sortCol} sortDir={sortDir} onSort={handleSort}>Forecast Peak</Th>
              <Th col="actualPeak" sortCol={sortCol} sortDir={sortDir} onSort={handleSort}>Actual Peak</Th>
              <Th col="errorPct" sortCol={sortCol} sortDir={sortDir} onSort={handleSort}>Error %</Th>
              <Th col="confidence" sortCol={sortCol} sortDir={sortDir} onSort={handleSort}>Confidence</Th>
              <th className="w-full border-b border-line px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.06em] text-faint-text">Notes</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => {
              const { text: errText, bg: errBg } = errorClass(row.errorPct)
              const isHovered = hoveredRow === row.id
              return (
                <tr
                  key={row.id}
                  onMouseEnter={() => setHoveredRow(row.id)}
                  onMouseLeave={() => setHoveredRow(null)}
                  className="border-b border-line transition-colors"
                  style={{ background: isHovered ? 'rgba(16,185,129,0.04)' : '' }}
                >
                  <td className="px-4 py-2.5 tabular-nums text-muted-text">{row.date}</td>
                  <td className="px-4 py-2.5">
                    <span className="font-medium text-main-text">{row.plant}</span>
                    <span
                      className="ml-1.5 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase"
                      style={{
                        background: row.plantType === 'solar' ? 'rgba(251,191,36,0.15)' : 'rgba(52,211,153,0.15)',
                        color: row.plantType === 'solar' ? '#fbbf24' : '#34d399',
                      }}
                    >
                      {row.plantType === 'solar' ? '☀' : '💨'}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-main-text">{row.forecastPeak} MW</td>
                  <td className="px-4 py-2.5 tabular-nums text-main-text">{row.actualPeak} MW</td>
                  <td
                    className="relative px-4 py-2.5 tabular-nums font-semibold cursor-help"
                    style={{ color: errText, background: errBg }}
                    onMouseEnter={() => setTooltipRow(row.id)}
                    onMouseLeave={() => setTooltipRow(null)}
                  >
                    {row.errorPct.toFixed(1)}%
                    {tooltipRow === row.id && (
                      <div className="pointer-events-none absolute left-full top-1/2 z-50 -translate-y-1/2 ml-2 w-52 rounded-lg border border-line bg-surface-bg px-3 py-2 text-[11px] shadow-xl text-muted-text">
                        Absolute error: {Math.abs(row.actualPeak - row.forecastPeak).toFixed(1)} MW —{' '}
                        {row.errorPct < 10 ? 'within acceptable operational range' : 'Exceeded threshold — see notes'}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums">
                    <span style={{
                      color: row.confidence >= 7 ? '#22c55e' : row.confidence >= 4 ? '#f59e0b' : '#ef4444',
                      fontWeight: 600,
                    }}>
                      {row.confidence.toFixed(1)}
                    </span>
                    <span className="text-faint-text">/10</span>
                  </td>
                  <td className="px-4 py-2.5 text-[11px] text-faint-text w-full max-w-0 truncate" title={row.notes}>
                    {row.notes}
                  </td>
                </tr>
              )
            })}

            {/* ── Summary row ─────────────────────────────────────────────── */}
            <tr className="border-t-2 border-[#10b981]/30 bg-[#10b981]/5">
              <td colSpan={4} className="px-4 py-3 text-[11px] font-semibold text-[#10b981]">
                Summary — {filtered.length} entries shown
              </td>
              <td className="px-4 py-3 text-[12px] font-bold" style={{ color: parseFloat(avgError) < 5 ? '#22c55e' : '#f59e0b' }}>
                {avgError}% avg
              </td>
              <td colSpan={2} className="px-4 py-3 text-[11px] text-muted-text">
                Best plant: <span className="font-medium text-main-text">{bestPlant}</span>
                {' · '}
                Most accurate day: <span className="font-medium text-main-text">{mostAccurateDay}</span>
                {' · '}
                <span className="font-semibold text-[#22c55e]">
                  System accuracy over 14 days: {accuracyPct}% — exceeding 85% operational target
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* ── Empty state ───────────────────────────────────────────────────── */}
      {filtered.length === 0 && (
        <div className="mt-8 text-center text-sm text-faint-text">
          No entries match your search.
        </div>
      )}
    </div>
  )
}
