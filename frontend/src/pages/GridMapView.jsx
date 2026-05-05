import { useState, useEffect } from 'react'
import { fetchForecast, PLANTS } from '../api/client'
import { useLanguage } from '../context/LanguageContext'

const plantCoordinates = {
  PVG_S1: { x: 285, y: 195, name: 'Pavagada Solar 1', type: 'solar' },
  PVG_S2: { x: 290, y: 200, name: 'Pavagada Solar 2', type: 'solar' },
  MIX_S1: { x: 265, y: 210, name: 'Chitradurga Solar', type: 'solar' },
  GAD_W1: { x: 210, y: 165, name: 'Gadag Wind 1', type: 'wind' },
  GAD_W2: { x: 215, y: 170, name: 'Gadag Wind 2', type: 'wind' },
  MIX_W1: { x: 245, y: 180, name: 'Raichur Wind', type: 'wind' },
}

const computeConfidence = (p10, p90, capacityMw) => {
  if (!p10 || !p90 || p10.length === 0) return 8.0 // default
  const avgWidth = p90.reduce((sum, v, i) => sum + (v - p10[i]), 0) / p90.length
  const score = Math.max(1, Math.min(10, 10 - (avgWidth / capacityMw) * 10))
  return Math.round(score * 10) / 10
}

const scoreColor = (score) => {
  if (score >= 7) return '#22c55e'
  if (score >= 4) return '#f59e0b'
  return '#ef4444'
}

export default function GridMapView() {
  const { t } = useLanguage()
  const [forecasts, setForecasts] = useState({})
  const [hoveredPlant, setHoveredPlant] = useState(null)

  useEffect(() => {
    const loadData = async () => {
      const results = await Promise.all(
        PLANTS.map(p => fetchForecast(p.id, 0).then(res => ({ id: p.id, data: res.data, capacity: p.capacityMw })))
      )
      const newData = {}
      results.forEach(r => {
        if (r.data) {
          const score = computeConfidence(r.data.p10, r.data.p90, r.capacity)
          const istHour = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' })).getHours()
          const currentP50 = r.data.p50?.[istHour] || 0
          newData[r.id] = { score, color: scoreColor(score), currentP50 }
        }
      })
      setForecasts(newData)
    }

    loadData()
    const interval = setInterval(loadData, 60000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex h-full w-full items-center justify-center p-6">
      <div className="relative h-[500px] w-full max-w-[600px] overflow-hidden rounded-xl border border-line bg-[#1e2130] shadow-xl">
        
        {/* Karnataka Map SVG */}
        <svg viewBox="0 0 500 500" className="h-full w-full opacity-80" preserveAspectRatio="xMidYMid meet">
          <path
            d="M 180,20 L 220,15 L 280,25 L 320,40 L 350,35 L 380,50 L 390,80 L 400,110 L 390,140 L 410,170 L 400,200 L 380,230 L 360,250 L 340,280 L 310,300 L 290,330 L 270,350 L 250,370 L 220,380 L 200,360 L 180,340 L 160,310 L 150,280 L 140,250 L 130,220 L 120,190 L 110,160 L 120,130 L 130,100 L 150,70 L 160,45 Z"
            fill="#151722"
            stroke="#3b82f6"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />

          {/* Cluster Boundaries */}
          <ellipse cx="280" cy="200" rx="40" ry="30" fill="none" stroke="#5a5d72" strokeWidth="1" strokeDasharray="4 4" />
          <text x="325" y="200" fill="#8b8fa8" fontSize="10">Cluster A</text>

          <ellipse cx="220" cy="170" rx="35" ry="25" fill="none" stroke="#5a5d72" strokeWidth="1" strokeDasharray="4 4" />
          <text x="170" y="150" fill="#8b8fa8" fontSize="10">Cluster B</text>

          {/* Major Cities */}
          <circle cx="295" cy="255" r="2" fill="#8b8fa8" />
          <text x="300" y="258" fill="#8b8fa8" fontSize="10">Bengaluru</text>
          
          <circle cx="195" cy="175" r="2" fill="#8b8fa8" />
          <text x="200" y="178" fill="#8b8fa8" fontSize="10">Hubli</text>

          <circle cx="250" cy="295" r="2" fill="#8b8fa8" />
          <text x="255" y="298" fill="#8b8fa8" fontSize="10">Mysuru</text>

          {/* Plants */}
          {Object.entries(plantCoordinates).map(([id, p]) => {
            const data = forecasts[id]
            const color = data?.color || '#5a5d72'
            return (
              <g 
                key={id} 
                onMouseEnter={() => setHoveredPlant(id)}
                onMouseLeave={() => setHoveredPlant(null)}
                className="cursor-pointer transition-transform hover:scale-110"
              >
                <circle cx={p.x} cy={p.y} r="16" fill={color} fillOpacity="0.2" className="animate-pulse" />
                <circle cx={p.x} cy={p.y} r="6" fill={color} />
                <text x={p.x - 4} y={p.y + 3} fontSize="8" fill="#151722" fontWeight="bold">
                  {p.type === 'solar' ? '☀' : '💨'}
                </text>
              </g>
            )
          })}
        </svg>

        {/* Legend */}
        <div className="absolute bottom-4 left-4 rounded-lg border border-line bg-surface-bg/90 p-3 text-xs backdrop-blur-sm">
          <div className="mb-2 font-medium text-main-text">Confidence Level</div>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-[#22c55e]" /> <span className="text-muted-text">High (7-10)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-[#f59e0b]" /> <span className="text-muted-text">Medium (4-6)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-[#ef4444]" /> <span className="text-muted-text">Low (1-3)</span>
            </div>
            <div className="mt-1 flex items-center gap-3 border-t border-line pt-1.5">
              <span className="text-muted-text">☀ Solar</span>
              <span className="text-muted-text">💨 Wind</span>
            </div>
          </div>
        </div>

        {/* Hover Tooltip */}
        {hoveredPlant && forecasts[hoveredPlant] && (
          <div className="absolute right-4 top-4 w-64 rounded-lg border border-line bg-surface-bg/95 p-4 shadow-2xl backdrop-blur-sm">
            <h3 className="mb-1 font-medium text-main-text">{plantCoordinates[hoveredPlant].name}</h3>
            <div className="flex flex-col gap-2 text-sm">
              <div className="flex justify-between border-b border-line pb-1">
                <span className="text-muted-text">Current P50:</span>
                <span className="font-semibold text-main-text">{forecasts[hoveredPlant].currentP50.toFixed(1)} MW</span>
              </div>
              <div className="flex justify-between border-b border-line pb-1">
                <span className="text-muted-text">Confidence:</span>
                <span className="font-semibold" style={{ color: forecasts[hoveredPlant].color }}>
                  {forecasts[hoveredPlant].score} / 10
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
