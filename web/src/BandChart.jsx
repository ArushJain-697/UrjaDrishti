import React, { useState } from 'react'

const TIER_COLOR = { GREEN: 'var(--green)', AMBER: 'var(--amber)', RED: 'var(--red)' }
const W = 760, H = 300, PAD = { l: 44, r: 12, t: 14, b: 46 }

// One plant-day: conformal P10-P90 band, the filed schedule (P50), the deviation-free band
// around it, the three raw NWP physics forecasts, what actually happened, and a tier strip.
export default function BandChart({ plant, capacity, showNwp }) {
  const [hover, setHover] = useState(null)
  const n = plant.hours.length
  const x = (i) => PAD.l + (i / (n - 1)) * (W - PAD.l - PAD.r)
  const y = (v) => PAD.t + (1 - v / capacity) * (H - PAD.t - PAD.b)
  const path = (arr) => arr.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('')
  const band = path(plant.p90) + plant.p10.map((v, i) => n - 1 - i).map((i) => `L${x(i).toFixed(1)},${y(plant.p10[i]).toFixed(1)}`).join('') + 'Z'
  const fb = plant.free_band_mw
  const freeBand = path(plant.p50.map((v) => Math.min(capacity, v + fb))) +
    plant.p50.map((_, i) => n - 1 - i).map((i) => `L${x(i).toFixed(1)},${y(Math.max(0, plant.p50[i] - fb)).toFixed(1)}`).join('') + 'Z'

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" onMouseLeave={() => setHover(null)}
      onMouseMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect()
        const px = ((e.clientX - r.left) / r.width) * W
        const i = Math.round(((px - PAD.l) / (W - PAD.l - PAD.r)) * (n - 1))
        setHover(i >= 0 && i < n ? i : null)
      }}>
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <g key={f}>
          <line x1={PAD.l} x2={W - PAD.r} y1={y(f * capacity)} y2={y(f * capacity)} className="grid" />
          <text x={PAD.l - 6} y={y(f * capacity) + 4} className="axis" textAnchor="end">{Math.round(f * capacity)}</text>
        </g>
      ))}
      <path d={freeBand} className="freeband" />
      <path d={band} className="band" />
      {showNwp && Object.entries(plant.nwp).map(([m, arr]) => <path key={m} d={path(arr)} className={`nwp nwp-${m}`} />)}
      <path d={path(plant.p50)} className="p50" />
      {plant.actual.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r={3} className="actual" />)}
      {plant.tier.map((t, i) => (
        <rect key={i} x={x(i) - (W - PAD.l - PAD.r) / (2 * (n - 1))} width={(W - PAD.l - PAD.r) / (n - 1)}
          y={H - PAD.b + 10} height={10} fill={TIER_COLOR[t]} opacity={0.9} />
      ))}
      {plant.hours.map((h, i) => (i % 3 === 0 ? <text key={i} x={x(i)} y={H - 6} className="axis" textAnchor="middle">{String(h).padStart(2, '0')}:00</text> : null))}
      <text x={8} y={PAD.t + 4} className="axis">MW</text>
      {hover !== null && (
        <g>
          <line x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={H - PAD.b} className="cursor" />
          <foreignObject x={Math.min(x(hover) + 8, W - 190)} y={PAD.t} width={180} height={120}>
            <div className="tip">
              <b>{String(plant.hours[hover]).padStart(2, '0')}:00</b> <span className={`pill ${plant.tier[hover]}`}>{plant.tier[hover]}</span><br />
              schedule {plant.p50[hover].toFixed(1)} MW<br />
              band {plant.p10[hover].toFixed(1)}–{plant.p90[hover].toFixed(1)}<br />
              actual {plant.actual[hover].toFixed(1)}
            </div>
          </foreignObject>
        </g>
      )}
    </svg>
  )
}
