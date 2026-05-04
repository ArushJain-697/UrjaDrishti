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

function ChartTooltip({ active, payload, label, lineColor = '#10b981' }) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  if (!row) return null
  const { p50, p10, p90 } = row
  const w = p90 - p10
  const h = Number(label)
  const hh = String(h).padStart(2, '0')

  return (
    <div className="rounded-lg border border-line bg-hover-bg px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-medium text-main-text">
        {hh}:00 <span className="text-faint-text">IST</span>
      </p>
      <p style={{ color: lineColor }}>P50: {p50.toFixed(1)} MW</p>
      <p className="text-muted-text">P10: {p10.toFixed(1)} MW</p>
      <p className="text-muted-text">P90: {p90.toFixed(1)} MW</p>
      <p className="mt-1 text-[11px] text-faint-text">Interval width: {w.toFixed(1)} MW</p>
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
  const lineColor = meta.type === 'wind' ? '#34d399' : '#10b981'
  const bandFill =
    meta.type === 'wind' ? 'rgba(167, 139, 250, 0.18)' : 'rgba(59, 130, 246, 0.18)'
  // BUG 3 FIX: chart background colour used to erase below p10 in the band
  const chartBg = 'var(--hover-bg)'

  // BUG 3 FIX: data only needs p10, p50, p90 — no more stacking helpers
  const data = forecast.hours.map((h, i) => ({
    hour: h,
    p50: forecast.p50[i],
    p10: forecast.p10[i],
    p90: forecast.p90[i],
  }))

  return (
    <div
      className={`h-[320px] w-full rounded-xl border border-line bg-hover-bg p-2 ${className}`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--line)" strokeOpacity={0.5} vertical={false} />
          <XAxis
            dataKey="hour"
            tickFormatter={(v) => `${String(v).padStart(2, '0')}:00`}
            stroke="var(--line)"
            tick={{ fill: 'var(--muted-text)', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: 'var(--line)' }}
          />
          <YAxis
            stroke="var(--line)"
            tick={{ fill: 'var(--muted-text)', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: 'var(--line)' }}
            width={44}
            label={{
              value: 'MW',
              angle: -90,
              position: 'insideLeft',
              fill: 'var(--faint-text)',
              fontSize: 11,
            }}
          />
          <Tooltip
            content={(tipProps) => <ChartTooltip {...tipProps} lineColor={lineColor} />}
            cursor={{ stroke: 'var(--line)', strokeOpacity: 0.6 }}
          />

          {/*
            BUG 3 FIX: Correct band rendering.
            1. Draw p90 area filled from 0 up to p90 with band colour.
            2. Draw p10 area filled from 0 up to p10 with chart background colour,
               which paints over the lower portion and leaves only the p10→p90 band visible.
            3. Draw the p50 line on top.
            This avoids the stacked-Area hack that caused the band to visually
            extend to zero when p10 was near 0.
          */}
          <Area
            type="monotone"
            dataKey="p90"
            stroke="none"
            fill={bandFill}
            isAnimationActive
            animationDuration={800}
          />
          <Area
            type="monotone"
            dataKey="p10"
            stroke="none"
            fill={chartBg}
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
