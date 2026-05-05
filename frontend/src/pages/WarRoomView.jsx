import { useCallback, useEffect, useMemo, useState } from 'react'
import { X, AlertTriangle, CheckCircle, Info, RefreshCw } from 'lucide-react'
import { PLANTS, plantMeta, fetchForecast, fetchAlerts } from '../api/client'


// ── Design tokens ────────────────────────────────────────────────────────────
const C = {
  bg:         '#060d06',
  card:       '#0d1a0d',
  cardHover:  '#111f11',
  bar:        '#0a140a',
  bGreen:     '#00c853',
  bAmber:     '#ffab00',
  bRed:       '#ff3d00',
  line:       '#1a2e1a',
  textPri:    '#e8f5e8',
  textSec:    '#7aad7a',
  textMut:    '#4a6b4a',
  aGreen:     '#00e676',
  aTeal:      '#00bcd4',
  aAmber:     '#ffab00',
  aRed:       '#ff5252',
  ringBg:     '#1a2e1a',
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function scoreColor(s) {
  if (s == null) return C.textMut
  return s >= 7 ? C.bGreen : s >= 4 ? C.bAmber : C.bRed
}

function computeConfidence(p10, p90, cap) {
  if (!p10?.length || !p90?.length || !cap) return null
  const avg = p90.reduce((s, v, i) => s + (v - p10[i]), 0) / p90.length
  return Math.round(Math.max(1, Math.min(10, 10 - (avg / cap) * 10)) * 10) / 10
}

// ── SVG confidence ring ──────────────────────────────────────────────────────
function Ring({ score, color, size = 150 }) {
  const R = size * 0.36, C2 = 2 * Math.PI * R
  const dash = score != null ? (score / 10) * C2 : 0
  const cx = size / 2, cy = size / 2
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)', position: 'absolute' }}>
      <circle cx={cx} cy={cy} r={R} fill="none" stroke={C.ringBg} strokeWidth={5} />
      <circle cx={cx} cy={cy} r={R} fill="none" stroke={color} strokeWidth={5}
        strokeLinecap="round"
        strokeDasharray={`${dash} ${C2}`}
        style={{ filter: `drop-shadow(0 0 5px ${color})`, transition: 'stroke-dasharray 1s ease' }}
      />
    </svg>
  )
}

// ── Corner brackets (tactical UI feel) ──────────────────────────────────────
function Corners({ color }) {
  const s = { position: 'absolute', width: 10, height: 10, borderColor: color, borderStyle: 'solid', opacity: 0.6 }
  return (
    <>
      <div style={{ ...s, top: 5, left: 5, borderWidth: '1.5px 0 0 1.5px' }} />
      <div style={{ ...s, top: 5, right: 5, borderWidth: '1.5px 1.5px 0 0' }} />
      <div style={{ ...s, bottom: 5, left: 5, borderWidth: '0 0 1.5px 1.5px' }} />
      <div style={{ ...s, bottom: 5, right: 5, borderWidth: '0 1.5px 1.5px 0' }} />
    </>
  )
}

// ── Skeleton card ────────────────────────────────────────────────────────────
function Skeleton() {
  return (
    <div style={{ background: C.card, border: `2px solid ${C.line}`, borderRadius: 8, padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
      {[35, 100, 55, 22].map((w, i) => (
        <div key={i} className="shimmer-wr" style={{ height: i === 1 ? 52 : 13, width: `${w}%`, borderRadius: 4 }} />
      ))}
    </div>
  )
}

// ── Alert type icon ──────────────────────────────────────────────────────────
function AIcon({ type }) {
  if (type === 'warning') return <AlertTriangle size={10} color={C.aAmber} />
  if (type === 'success') return <CheckCircle size={10} color={C.aGreen} />
  return <Info size={10} color={C.aTeal} />
}

// ── Plant card ───────────────────────────────────────────────────────────────
function PlantCard({ plant, forecast, alerts, loading }) {
  const [hov, setHov] = useState(false)
  const meta = plantMeta(plant.id)

  const istHour = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' })).getHours()
  const p50 = forecast?.p50?.[istHour] ?? 0
  const p10 = forecast?.p10?.[istHour] ?? 0
  const p90 = forecast?.p90?.[istHour] ?? 0
  const score = forecast ? computeConfidence(forecast.p10, forecast.p90, plant.capacityMw) : null
  const col = scoreColor(score)
  const alert0 = alerts?.[0]
  const aBarCol = alert0?.type === 'warning' ? C.aAmber : alert0?.type === 'success' ? C.aGreen : C.aTeal

  if (loading) return <Skeleton />

  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: hov ? C.cardHover : C.card,
        border: `2px solid ${col}`,
        borderRadius: 8,
        padding: '10px 12px',
        display: 'flex', flexDirection: 'column', gap: 0,
        position: 'relative', overflow: 'hidden',
        boxShadow: hov ? `0 0 18px ${col}40` : `0 0 6px ${col}25`,
        transition: 'all 0.25s',
        animation: 'plant-pulse 3s ease-in-out infinite',
      }}
    >
      <Corners color={col} />

      {/* Top: id + name + cluster */}
      <div style={{ marginBottom: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
          <span style={{ fontSize: 9, letterSpacing: '0.14em', color: C.textMut, textTransform: 'uppercase' }}>{plant.id}</span>
          <span style={{ fontSize: 8, padding: '1px 5px', border: `1px solid ${C.line}`, borderRadius: 3, color: C.textSec, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            CLU-{meta.cluster}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: C.textPri, lineHeight: 1.2 }}>{meta.name}</span>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: meta.type === 'solar' ? '#3b82f6' : '#a78bfa', boxShadow: `0 0 4px ${meta.type === 'solar' ? '#3b82f6' : '#a78bfa'}`, flexShrink: 0 }} />
        </div>
      </div>

      {/* Center: confidence ring */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', minHeight: 150 }}>
        <Ring score={score} color={col} size={180} />
        <div style={{ textAlign: 'center', lineHeight: 1, zIndex: 1 }}>
          <div style={{ fontSize: 38, fontWeight: 700, color: col, fontFamily: 'monospace', textShadow: `0 0 14px ${col}` }}>
            {score?.toFixed(1) ?? '—'}
          </div>
          <div style={{ fontSize: 12, color: C.textMut }}>/10</div>
        </div>
      </div>

      {/* Bottom stats */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 4 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span style={{ fontSize: 10, color: C.textMut, letterSpacing: '0.06em' }}>P50 NOW</span>
          <span style={{ fontSize: 16, fontWeight: 700, fontFamily: 'monospace', color: C.aTeal }}>{p50.toFixed(1)} MW</span>
        </div>
        <div style={{ fontSize: 10, color: C.textMut, textAlign: 'right' }}>
          P10 {p10.toFixed(1)} · P90 {p90.toFixed(1)} MW
        </div>
        {alert0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 3, paddingTop: 4, borderTop: `1px solid ${C.line}` }}>
            <AIcon type={alert0.type} />
            <span style={{ fontSize: 9.5, color: C.textSec, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
              {(alert0.message ?? '').replace(/^[\p{Emoji}\s]+/u, '').slice(0, 60)}
            </span>
          </div>
        )}
      </div>

      {/* Bottom accent bar */}
      {alert0 && (
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 3, background: aBarCol, boxShadow: `0 0 6px ${aBarCol}` }} />
      )}
    </div>
  )
}

// ── Live IST clock ────────────────────────────────────────────────────────────
function Clock() {
  const [t, setT] = useState('')
  useEffect(() => {
    const tick = () => setT(new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false }))
    tick(); const id = setInterval(tick, 1000); return () => clearInterval(id)
  }, [])
  return <span style={{ fontFamily: 'monospace', fontSize: 26, fontWeight: 700, color: C.aGreen, letterSpacing: '0.05em', textShadow: `0 0 10px ${C.aGreen}88` }}>{t}</span>
}

// ── Countdown + progress bar ──────────────────────────────────────────────────
function Countdown({ total, onRefresh }) {
  const [r, setR] = useState(total)
  useEffect(() => {
    setR(total)
    const id = setInterval(() => setR(v => { if (v <= 1) { onRefresh?.(); return total } return v - 1 }), 1000)
    return () => clearInterval(id)
  }, [total, onRefresh])
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
      <span style={{ fontSize: 9, color: C.textMut, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Next refresh {r}s</span>
      <div style={{ width: 72, height: 2, background: C.line, borderRadius: 1 }}>
        <div style={{ height: '100%', borderRadius: 1, background: C.aTeal, width: `${(r / total) * 100}%`, transition: 'width 1s linear' }} />
      </div>
    </div>
  )
}

// ── Bottom stat pill ──────────────────────────────────────────────────────────
function Pill({ label, value, color }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
      <span style={{ fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', color: C.textMut }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 700, fontFamily: 'monospace', color }}>{value}</span>
    </div>
  )
}

// ── Main WarRoomView ──────────────────────────────────────────────────────────
export default function WarRoomView({ onExit }) {
  const [forecasts, setForecasts] = useState({})
  const [alerts, setAlerts]       = useState({})
  const [loading, setLoading]     = useState(new Set(PLANTS.map(p => p.id)))
  const [lastUpd, setLastUpd]     = useState(null)
  const [usingMock, setUsingMock] = useState(false)

  const [fetchError, setFetchError] = useState('')

  const fetchAll = useCallback(async () => {
    let anyMock = false
    const newFc = {}

    await Promise.all(PLANTS.map(async (p) => {
      try {
        const res = await fetch('http://localhost:8000/api/forecast/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': 'kredl-dev-key',
          },
          body: JSON.stringify({ plant_id: p.id, hours_of_actuals: 0 }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        newFc[p.id] = data
      } catch (err) {
        anyMock = true
        setFetchError(String(err?.message || err))
        // use fetchForecast mock fallback
        const fb = await fetchForecast(p.id, 0, 'Normal Day')
        newFc[p.id] = fb.data
      }
    }))

    setForecasts(newFc)
    setUsingMock(anyMock)
    if (!anyMock) setFetchError('')
    setLoading(new Set())
    setLastUpd(new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false }))


    const aResults = await Promise.allSettled(
      PLANTS.map((p, i) => {
        const fc = newFc[p.id]; if (!fc) return Promise.resolve({ alerts: [] })
        return fetchAlerts(p.id, fc.p50, fc.hours)
      })
    )
    const newAl = {}
    aResults.forEach((r, i) => {
      const raw = r.status === 'fulfilled' ? r.value : {}
      newAl[PLANTS[i].id] = raw?.data?.alerts ?? raw?.alerts ?? []
    })
    setAlerts(newAl)
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  // Keep retrying every 15s while on mock until real data loads
  useEffect(() => {
    if (!usingMock) return
    const id = setInterval(() => { fetchAll() }, 15000)
    return () => clearInterval(id)
  }, [usingMock, fetchAll])

  const istHour = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' })).getHours()

  const clusterTotals = useMemo(() => {
    let A = 0, B = 0
    for (const p of PLANTS) {
      const v = forecasts[p.id]?.p50?.[istHour] ?? 0
      if (p.cluster === 'A') A += v; else B += v
    }
    return { A: A.toFixed(1), B: B.toFixed(1) }
  }, [forecasts, istHour])

  const carbon = useMemo(() => {
    let mwh = 0
    for (const p of PLANTS) { const fc = forecasts[p.id]; if (fc?.p50) mwh += fc.p50.reduce((s, v) => s + v, 0) }
    return Math.round(mwh * 0.82).toLocaleString('en-IN')
  }, [forecasts])

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: C.bg,
      backgroundImage: 'linear-gradient(rgba(0,230,118,0.022) 1px,transparent 1px),linear-gradient(90deg,rgba(0,230,118,0.022) 1px,transparent 1px)',
      backgroundSize: '48px 48px',
      display: 'flex', flexDirection: 'column',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Scanline overlay */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 10001,
        background: 'repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.012) 2px,rgba(0,0,0,0.012) 4px)' }} />

      {/* Slow scan line */}
      <div style={{ position: 'fixed', left: 0, right: 0, height: 2, zIndex: 10002, pointerEvents: 'none',
        background: `linear-gradient(transparent,${C.aGreen}18,transparent)`,
        animation: 'war-scan 8s linear infinite', top: 0 }} />

      {/* ── Top bar ── */}
      <div style={{ height: 56, background: C.bar, borderBottom: `1px solid ${C.line}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', flexShrink: 0, position: 'relative' }}>
        {/* top accent line */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(to right, transparent, ${C.aGreen}, transparent)` }} />

        {/* Left */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: C.aGreen, boxShadow: `0 0 8px ${C.aGreen}` }} />
          <span style={{ color: '#3b82f6', fontSize: 15, fontWeight: 800, letterSpacing: '0.06em' }}>URJADRISHTI</span>
          <span style={{ fontSize: 9, padding: '2px 6px', border: `1px solid #3b82f620`, borderRadius: 3, color: '#3b82f680', letterSpacing: '0.08em' }}>KREDL / KSPDCL</span>
        </div>

        {/* Center title */}
        <div style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', textAlign: 'center' }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: C.textPri }}>
            WAR ROOM <span style={{ color: C.aGreen }}>—</span> LIVE GRID MONITOR
          </div>
          {usingMock ? (
            <div style={{ fontSize: 9, color: C.aAmber, letterSpacing: '0.1em', marginTop: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
              <RefreshCw size={8} style={{ animation: 'war-live-pulse 1s linear infinite' }} />
              {fetchError ? `ERR: ${fetchError.slice(0, 60)}` : 'RETRYING — CONNECTING TO BACKEND'}
            </div>
          ) : (
            <div style={{ fontSize: 9, color: C.textMut, letterSpacing: '0.12em', marginTop: 2 }}>
              KARNATAKA RENEWABLE ENERGY · 6 PLANTS · 2 CLUSTERS
            </div>
          )}
        </div>

        {/* Right */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <Clock />
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: C.aGreen, boxShadow: `0 0 6px ${C.aGreen}`, animation: 'war-live-pulse 1.5s ease-in-out infinite' }} />
            <span style={{ fontSize: 10, color: C.aGreen, fontWeight: 800, letterSpacing: '0.12em' }}>LIVE</span>
          </div>
          <button
            onClick={onExit}
            style={{ background: 'transparent', border: `1px solid ${C.line}`, borderRadius: 4, padding: '4px 10px', cursor: 'pointer', color: C.textMut, fontSize: 10, display: 'flex', alignItems: 'center', gap: 4, transition: 'all 0.2s', letterSpacing: '0.06em' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = C.aRed; e.currentTarget.style.color = C.aRed }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = C.line; e.currentTarget.style.color = C.textMut }}
          >
            <X size={11} /> EXIT WAR ROOM
          </button>
        </div>
      </div>

      {/* ── 3×2 Plant grid ── */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gridTemplateRows: 'repeat(2,1fr)', gap: 8, padding: 12, overflow: 'hidden' }}>
        {PLANTS.map(p => (
          <PlantCard
            key={p.id}
            plant={p}
            forecast={forecasts[p.id]}
            alerts={alerts[p.id]}
            loading={loading.has(p.id)}
          />
        ))}
      </div>

      {/* ── Bottom bar ── */}
      <div style={{ height: 44, background: C.bar, borderTop: `1px solid ${C.line}`, display: 'flex', alignItems: 'center', justifyContent: 'space-around', padding: '0 20px', flexShrink: 0, gap: 4 }}>
        <Pill label="Cluster A Total" value={`${clusterTotals.A} MW`} color={C.aTeal} />
        <div style={{ width: 1, height: 20, background: C.line }} />
        <Pill label="Cluster B Total" value={`${clusterTotals.B} MW`} color={C.aTeal} />
        <div style={{ width: 1, height: 20, background: C.line }} />
        <Pill label="Carbon Avoided" value={`${carbon} t CO₂`} color={C.aGreen} />
        <div style={{ width: 1, height: 20, background: C.line }} />
        <Pill label="Last Updated" value={lastUpd ?? '—'} color={C.textSec} />
        <div style={{ width: 1, height: 20, background: C.line }} />
        <Countdown total={60} onRefresh={fetchAll} />
      </div>
    </div>
  )
}
