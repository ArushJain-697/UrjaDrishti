import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { plantMeta } from '../api/client'

function ChartTooltip({ active, payload, label, lineColor = '#3b82f6' }) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  if (!row) return null
  const p50 = row.p50
  const p10 = row.p10
  const p90 = row.p90
  const w = p90 - p10
  const h = Number(label)
  const hh = String(h).padStart(2, '0')

  return (
    <div className="rounded-lg border border-[#2a2d3e] bg-[#1e2130] px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-medium text-[#e8eaf0]">
        {hh}:00 <span className="text-[#5a5d72]">IST</span>
      </p>
      <p style={{ color: lineColor }}>P50: {p50.toFixed(1)} MW</p>
      <p className="text-[#8b8fa8]">P10: {p10.toFixed(1)} MW</p>
      <p className="text-[#8b8fa8]">P90: {p90.toFixed(1)} MW</p>
      <p className="mt-1 text-[11px] text-[#5a5d72]">Interval width: {w.toFixed(1)} MW</p>
    </div>
  )
}

export default function ForecastChart({
  forecast,
  plantId,
  intradayNowHour,
  className = '',
}) {
  const meta = plantMeta(plantId)
  const lineColor = meta.type === 'wind' ? '#a78bfa' : '#3b82f6'
  const bandFill =
    meta.type === 'wind' ? 'rgba(167, 139, 250, 0.2)' : 'rgba(59, 130, 246, 0.2)'

  const data = forecast.hours.map((h, i) => ({
    hour: h,
    p50: forecast.p50[i],
    p10: forecast.p10[i],
    p90: forecast.p90[i],
    p10base: forecast.p10[i],
    bandWidth: Math.max(0, forecast.p90[i] - forecast.p10[i]),
  }))

  return (
    <div className={`h-[320px] w-full rounded-xl border border-[#2a2d3e] bg-[#1e2130] p-2 ${className}`}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="#2a2d3e" strokeOpacity={0.5} vertical={false} />
          <XAxis
            dataKey="hour"
            tickFormatter={(v) => `${String(v).padStart(2, '0')}:00`}
            stroke="#2a2d3e"
            tick={{ fill: '#8b8fa8', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#2a2d3e' }}
          />
          <YAxis
            stroke="#2a2d3e"
            tick={{ fill: '#8b8fa8', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#2a2d3e' }}
            width={44}
            label={{
              value: 'MW',
              angle: -90,
              position: 'insideLeft',
              fill: '#5a5d72',
              fontSize: 11,
            }}
          />
          <Tooltip
            content={(tipProps) => <ChartTooltip {...tipProps} lineColor={lineColor} />}
            cursor={{ stroke: '#2a2d3e', strokeOpacity: 0.6 }}
          />
          <Area
            type="monotone"
            dataKey="p10base"
            stackId="band"
            stroke="none"
            fill="transparent"
            isAnimationActive
            animationDuration={800}
          />
          <Area
            type="monotone"
            dataKey="bandWidth"
            stackId="band"
            stroke="none"
            fill={bandFill}
            isAnimationActive
            animationDuration={800}
          />
          <Line
            type="monotone"
            dataKey="p50"
            stroke={lineColor}
            strokeWidth={2}
            dot={false}
            isAnimationActive
            animationDuration={800}
          />
          {typeof intradayNowHour === 'number' ? (
            <ReferenceLine
              x={intradayNowHour}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              label={{
                value: 'Now',
                position: 'top',
                fill: '#f59e0b',
                fontSize: 11,
              }}
            />
          ) : null}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
