import React, { useEffect, useMemo, useState } from 'react'
import BandChart from './BandChart.jsx'

const get = (u) => fetch(u).then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
const pct = (v, d = 0) => `${(v * 100).toFixed(d)}%`

export default function App() {
  const [sites, setSites] = useState([])
  const [days, setDays] = useState([])
  const [date, setDate] = useState(null)
  const [day, setDay] = useState(null)
  const [plantId, setPlantId] = useState('GDG_W1')
  const [metrics, setMetrics] = useState(null)
  const [showNwp, setShowNwp] = useState(true)

  useEffect(() => {
    get('/api/sites').then(setSites)
    get('/api/metrics').then(setMetrics)
    get('/api/days').then((d) => {
      setDays(d)
      setDate([...d].sort((a, b) => b.red_hours - a.red_hours)[0]?.date)
    })
  }, [])
  useEffect(() => { if (date) get(`/api/day/${date}`).then(setDay) }, [date])

  const villains = useMemo(() => [...days].sort((a, b) => b.red_hours - a.red_hours).slice(0, 5), [days])
  const site = sites.find((s) => s.plant_id === plantId)
  const plant = day?.plants?.[plantId]
  const kind = site?.kind

  return (
    <div className="page">
      <header>
        <div>
          <h1>UrjaDrishti <span className="dim">ಊರ್ಜಾ ದೃಷ್ಟಿ</span></h1>
          <p className="lede">Day-ahead solar &amp; wind forecasts for Karnataka that say how sure they are, hour by hour,
            and send the unsure hours to a person before the schedule is filed.</p>
        </div>
        <div className="badges">
          <span>real ERA5 truth</span><span>real ECMWF · GFS · ICON day-ahead runs</span><span>runs offline on a small CPU</span>
        </div>
      </header>

      <section className="card">
        <div className="row between">
          <h2>Replay desk</h2>
          <div className="row">
            <select value={plantId} onChange={(e) => setPlantId(e.target.value)}>
              {sites.map((s) => <option key={s.plant_id} value={s.plant_id}>{s.name} ({s.kind})</option>)}
            </select>
            <select value={date || ''} onChange={(e) => setDate(e.target.value)}>
              {days.map((d) => <option key={d.date} value={d.date}>{d.date} · {d.red_hours} RED h</option>)}
            </select>
            <label className="toggle"><input type="checkbox" checked={showNwp} onChange={(e) => setShowNwp(e.target.checked)} /> raw NWP</label>
          </div>
        </div>
        <div className="row villains">
          <span className="dim">Hardest days:</span>
          {villains.map((v) => <button key={v.date} className={v.date === date ? 'on' : ''} onClick={() => setDate(v.date)}>{v.date}</button>)}
        </div>
        {plant && site ? (
          <>
            <BandChart plant={plant} capacity={site.ac_mw} showNwp={showNwp} />
            <div className="legend">
              <span><i className="sw band" />P10–P90 (tier-calibrated)</span>
              <span><i className="sw p50" />filed schedule (P50)</span>
              <span><i className="sw freeband" />±10% free band</span>
              <span><i className="sw actual" />what happened</span>
              {showNwp && <span><i className="sw nwp" />ECMWF / GFS / ICON physics</span>}
            </div>
            <div className="stats">
              <div><b>{plant.review_hours.length}</b><span>hours sent to a dispatcher</span></div>
              <div><b>{plant.excess_mwh.toFixed(1)} MWh</b><span>outside the ±10% band</span></div>
              <div><b>{day.split === 'val' ? 'validation' : 'sealed test'}</b><span>split shown</span></div>
            </div>
          </>
        ) : <p className="dim">Loading… (run <code>python -m urja.train</code> if this stays empty)</p>}
      </section>

      {metrics?.val && <Trap m={metrics.val} />}
      {metrics && <Proof metrics={metrics} />}

      <footer className="dim">
        Plant output is simulated with physics (pvlib, a generic turbine curve) from real weather, because Karnataka plant SCADA is not public.
        The forecasts the model learns from are real archived NWP runs. See docs/HONESTY.md.
      </footer>
    </div>
  )
}

function Trap({ m }) {
  const [perTier, setPerTier] = useState(true)
  return (
    <section className="card">
      <div className="row between">
        <h2>The Flat-Band Trap</h2>
        <div className="seg">
          <button className={!perTier ? 'on' : ''} onClick={() => setPerTier(false)}>one band for all hours</button>
          <button className={perTier ? 'on' : ''} onClick={() => setPerTier(true)}>calibrated per tier</button>
        </div>
      </div>
      <p className="dim">An 80% band calibrated on all hours at once looks right on average. It is too wide on calm
        hours and too narrow on the stormy hours that cost deviation charges. Validation split, n hours per tier shown.</p>
      <div className="trap">
        {['solar', 'wind'].map((k) => {
          const src = perTier ? m.kinds[k].model : m.kinds[k].ablation.global_conformal
          return (
            <div key={k}>
              <h3>{k}</h3>
              {['GREEN', 'AMBER', 'RED'].map((t) => {
                const c = src.tiers[t]?.coverage_80 ?? 0
                return (
                  <div className="bar" key={t}>
                    <span className={`pill ${t}`}>{t}</span>
                    <div className="track"><div className="fill" style={{ width: pct(c) }} /><div className="target" /></div>
                    <b>{pct(c, 1)}</b>
                  </div>
                )
              })}
              <p className="dim small">RED is {pct(m.kinds[k].model.tiers.RED.share_hours)} of hours but
                {' '}{pct(m.kinds[k].model.tiers.RED.share_dsm_excess)} of the energy outside the free band.</p>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function Proof({ metrics }) {
  const split = metrics.test ? 'test' : 'val'
  const m = metrics[split]
  const edge = Object.values(metrics.edge || {})[0]
  return (
    <section className="card">
      <h2>Proof card <span className="dim small">({split === 'test' ? 'sealed test year, scored once' : 'validation split'} · {m.period.join(' → ')})</span></h2>
      <table>
        <thead><tr><th></th><th>model nMAE</th><th>best baseline</th><th>its nMAE</th><th>CRPS vs NWP ensemble</th><th>80% band coverage</th><th>energy outside free band</th></tr></thead>
        <tbody>
          {Object.entries(m.kinds).map(([k, v]) => {
            const bb = v.baselines[v.best_baseline]
            return (
              <tr key={k}>
                <td>{k}</td>
                <td>{pct(v.model.nmae, 2)}</td>
                <td>{v.best_baseline.replace('_', ' ')}</td>
                <td>{pct(bb.nmae, 2)} <span className="good">(−{pct(v.vs_best_baseline.nmae_reduction)})</span></td>
                <td>{v.model.crps.toFixed(4)} vs {v.baselines.nwp_ensemble.crps.toFixed(4)}</td>
                <td>{pct(v.model.coverage_80, 1)}</td>
                <td>−{pct(v.vs_best_baseline.dsm_excess_reduction)} vs {v.best_baseline.replace('_', ' ')}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {edge && (
        <p className="dim small">
          Edge ({edge.cpu.cpu}, 1 thread): quantile MLP {edge.kinds.wind.mlp_fp32.size_kb.toFixed(0)} KB fp32,
          {' '}{(edge.kinds.wind.mlp_fp32.ms_per_plant_day * 1000).toFixed(0)} µs per plant-day; int8 is smaller
          ({edge.kinds.wind.mlp_int8.size_kb.toFixed(0)} KB) but not faster at this size. Errors are % of plant capacity; solar scored on daylight hours only.
        </p>
      )}
    </section>
  )
}
